import pytest
from fastapi import HTTPException

from app.core.security import create_token, hash_password, token_user, verify_password
from app.main import create_task
from app.models.entities import User
from app.schemas import TaskIn


def test_jwt_round_trip(): assert token_user(create_token(17))==17
def test_password_hash():
 hashed=hash_password("secure demo password")
 assert verify_password("secure demo password",hashed)
 assert not verify_password("wrong",hashed)

@pytest.mark.asyncio
async def test_task_creation_rejects_cross_tenant_project():
    class Result:
        @staticmethod
        def scalar_one_or_none():
            return None

    class FakeDb:
        async def execute(self, statement):
            self.statement = statement
            return Result()

    user = User(id=1, email="member@example.test", password_hash="unused", tenant_id="tenant-a", role="member")
    with pytest.raises(HTTPException) as error:
        await create_task(TaskIn(project_id=42, title="Cross tenant"), user, FakeDb())
    assert error.value.status_code == 404
