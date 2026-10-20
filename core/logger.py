# pylint: disable=C0114
import atexit
import logging
import os
import queue
import sys
import threading
from logging.handlers import QueueHandler, QueueListener, TimedRotatingFileHandler

_LOG_QUEUE = queue.Queue()
class _LoggingState:
    listener: QueueListener | None = None


_state = _LoggingState()


def setup_logging() -> None:
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s %(name)s | %(message)s',
        datefmt='%Y-%m-%d, %H:%M:%S',
    )
    file_handler = TimedRotatingFileHandler(
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'logs.txt'),
        when='midnight',
        backupCount=5,
        encoding='utf-8',
    )
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setFormatter(formatter)
    _state.listener = QueueListener(
        _LOG_QUEUE, file_handler, console_handler, respect_handler_level=True
    )
    _state.listener.start()
    queue_handler = QueueHandler(_LOG_QUEUE)
    queue_handler.setFormatter(logging.Formatter('%(message)s'))
    logging.basicConfig(
        level=os.environ.get('LOG_LEVEL', 'INFO').upper(),
        handlers=[queue_handler],
        force=True,
    )


def _handle_unhandled_exception(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.getLogger('CRITICAL_ERROR').critical(
        'Unhandled exception - program crashed!', exc_info=(exc_type, exc_value, exc_traceback)
    )


def _handle_thread_exception(args) -> None:
    logging.getLogger('THREAD_ERROR').critical(
        f'Unhandled exception in thread: {args.thread.name}',
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def _cleanup() -> None:
    if _state.listener is not None:
        _state.listener.stop()


sys.excepthook = _handle_unhandled_exception
threading.excepthook = _handle_thread_exception
atexit.register(_cleanup)
