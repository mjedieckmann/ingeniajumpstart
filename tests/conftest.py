import pytest

from src.controllers.drive_controller import DriveController


@pytest.fixture
def drive_controller() -> DriveController:
    return DriveController()
