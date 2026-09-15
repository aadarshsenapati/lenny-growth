import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ArtifactNotFoundError
from app.db.database import get_db
from app.db.models import Artifact
from app.db.schemas import ArtifactResponse

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/session/{session_id}", response_model=list[ArtifactResponse])
async def list_session_artifacts(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[ArtifactResponse]:
    result = await db.execute(
        select(Artifact).where(Artifact.session_id == session_id).order_by(Artifact.created_at.desc())
    )
    return [ArtifactResponse.model_validate(a) for a in result.scalars().all()]


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ArtifactResponse:
    artifact = await db.get(Artifact, artifact_id)
    if not artifact:
        raise ArtifactNotFoundError(f"Artifact {artifact_id} not found.")
    return ArtifactResponse.model_validate(artifact)
