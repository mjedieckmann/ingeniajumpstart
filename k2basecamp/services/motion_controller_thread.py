import time
from functools import partial
from queue import Queue
from typing import Union

import ingenialogger
from ingenialink.exceptions import ILError
from ingeniamotion.exceptions import IMException
from PySide6.QtCore import QThread, Signal

from k2basecamp.utils.types import motion_controller_task, thread_report
from k2basecamp.utils.enums import Drive

logger = ingenialogger.get_logger(__name__)


class MotionControllerThread(QThread):
    """
    Thread to run ingeniamotion native functions or custom functions defined in the
    MotionControllerService.

    """

    task_errored: Signal = Signal(thread_report, arguments=["thread_report"])
    """Signal emitted when a task fails.
    The error message is returned by the thread"""

    task_completed: Signal = Signal(
        object,
        thread_report,
        arguments=["callback", "thread_report"],
    )
    """Signal emitted when a task is completed.
    A report [thread_report] is returned by the thread"""

    queue: Queue[Union[motion_controller_task, None]]
    """Task queue - the thread will work until the queue is empty and then
    wait for new tasks.
    """

    def __init__(self) -> None:
        """
        The constructor for MotionControllerThread class
        """
        self.__running = False
        self.queue = Queue()
        super().__init__()

    def run(self) -> None:
        """Run function.
        Emit a signal when it starts (started). Emits a report of
        :class:`~utils.types.thread_report` type using the task_completed
        signal. This report includes the method name, the output of the callback
        function, a timestamp, the duration and the exception raised during the
        callback, if any.
        If the task fails, a task_errored signal with the error message is emitted
        instead.

        """
        self.__running = True
        while self.__running:
            task = self.queue.get()
            if task is None:
                break
            timestamp = time.time()
            raised_exception = None
            output = None
            try:
                output = task.action(*task.args, **task.kwargs)
            except (
                IMException,
                ILError,
                ValueError,
                KeyError,
                FileNotFoundError,
                ConnectionError,
            ) as e:
                raised_exception = e
            duration = time.time() - timestamp
            if isinstance(task.callback, partial):
                func_name = task.callback.func.__qualname__
            else:
                func_name = task.callback.__qualname__
            drive = None
            if task.args:
                for arg in task.args:
                    if isinstance(arg, Drive):
                        drive = arg
                        break
            report = thread_report(
                drive,
                func_name,
                output,
                timestamp,
                duration,
                raised_exception,
            )
            if raised_exception is None:
                self.task_completed.emit(task.callback, report)
            else:
                logger.error(report)
                self.task_errored.emit(report)
            self.queue.task_done()

    def stop(self) -> None:
        self.__running = False
        self.queue.put(item=None)
