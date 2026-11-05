import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Trip, User
from app.schemas import TripCreate, TripResponse
from app.api.deps import get_current_user
from app.agents.trip_planner import graph

router = APIRouter(prefix="/api/trips", tags=["Trips"])

@router.post("", response_model=TripResponse, summary="创建新行程")
async def create_trip(
    trip_in: TripCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_trip = Trip(
        user_id=current_user.id,
        title=trip_in.title,
        origin=trip_in.origin,
        destination=trip_in.destination,
        start_date=trip_in.start_date,
        end_date=trip_in.end_date,
        budget=trip_in.budget,
        status="draft"
    )
    db.add(new_trip)
    await db.commit()
    await db.refresh(new_trip)
    return new_trip

@router.get("", response_model=list[TripResponse], summary="获取当前用户的所有行程")
async def get_my_trips(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Trip).where(Trip.user_id == current_user.id).order_by(Trip.created_at.desc())
    )
    trips = result.scalars().all()
    return trips

@router.delete("/{trip_id}", summary="删除行程")
async def delete_trip(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == current_user.id)
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在或无权删除")
    await db.delete(trip)
    await db.commit()
    return {"message": "删除成功"}

@router.post("/{trip_id}/plan-stream", summary="流式生成行程并实时返回日志")
async def plan_trip_stream(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id, Trip.user_id == current_user.id)
    )
    trip = result.scalars().first()
    if not trip:
        raise HTTPException(status_code=404, detail="行程不存在或无权访问")
        
    trip.status = "planning"
    await db.commit()

    async def event_generator():
        try:
            inputs = {
                "messages": [],
                "origin": trip.origin or "未定",
                "destination": trip.destination,
                "start_date": trip.start_date or "未定",
                "end_date": trip.end_date or "未定",
                "budget": trip.budget or "未定",
                "research_data": "",
                "draft_plan": "",
                "review_feedback": "",
                "review_passed": False,
                "retry_count": 0, # 👈 初始化重试次数
                "next_agent": ""
            }

            node_names = {
                "Supervisor": "👔 [主管] 正在思考下一步调度...",
                "Researcher": "🕵️ [情报官] 正在连接高德地图查询真实天气和景点...",
                "Tools": "🛠️ [系统] 高德工具执行中...",
                "CollectResearch": "📥 [情报官] 情报收集完毕，正在整理数据...",
                "Planner": "✍️ [规划师] 正在根据情报撰写行程草案...",
                "Auditor": "🧐 [审核员] 正在严格审查预算和行程合理性..."
            }

            final_draft_plan = ""

            async for event in graph.astream(inputs):
                for node_name, node_state in event.items():
                    log_msg = node_names.get(node_name, f"[{node_name}] 执行中...")
                    
                    # 抓取最新的草案
                    if node_name == "Planner" and isinstance(node_state, dict):
                        final_draft_plan = node_state.get("draft_plan", final_draft_plan)
                    if node_name == "Auditor" and isinstance(node_state, dict):
                        if node_state.get("review_passed") and "draft_plan" in node_state:
                            final_draft_plan = node_state["draft_plan"]

                    # 记录驳回日志
                    if node_name == "Auditor" and isinstance(node_state, dict) and not node_state.get("review_passed", True):
                        feedback = node_state.get("review_feedback", "")[:40]
                        log_msg += f"\n  ⚠️ 发现不合理：{feedback}... 打回重写！"
                    elif node_name == "Auditor" and node_state.get("review_passed"):
                        log_msg += " ✅ 审核通过！"
                    
                    yield f"data: {log_msg}\n\n"
                    await asyncio.sleep(0.1) 

            # 循环结束，直接使用抓取到的最终结果保存
            if not final_draft_plan:
                raise Exception("Agent 未能生成有效的行程草案，请稍后重试。")

            content = final_draft_plan.replace("```json", "").replace("```", "").strip()
            trip.plan_json = content
            trip.status = "ready"
            await db.commit()
            
            yield f"data: [DONE]\n\n"

        except Exception as e:
            trip.status = "draft"
            await db.commit()
            yield f"data: ❌ 发生错误：{str(e)}\n\n"
            yield f"data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")