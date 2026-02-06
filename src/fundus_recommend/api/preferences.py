from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from fundus_recommend.db.queries import set_user_preferences
from fundus_recommend.db.session import get_async_session
from fundus_recommend.models.schemas import PreferencesRequest, PreferencesResponse, TopicPreference

router = APIRouter(tags=["preferences"])


@router.post("/preferences", response_model=PreferencesResponse)
async def post_preferences(
    request: PreferencesRequest,
    session: AsyncSession = Depends(get_async_session),
):
    prefs = await set_user_preferences(
        session, request.user_id, [(p.topic, p.weight) for p in request.preferences]
    )
    return PreferencesResponse(
        user_id=request.user_id,
        preferences=[TopicPreference(topic=p.topic, weight=p.weight) for p in prefs],
    )
