"""Fusion add-in entry point. Keep the folder and this file named GearStudio."""

import traceback

_controller = None


def run(context):
    global _controller
    try:
        from .fusion.controller import Controller

        if _controller is not None:
            _controller.stop()
        _controller = Controller()
        _controller.start(context)
    except Exception:
        import adsk.core
        adsk.core.Application.get().userInterface.messageBox(
            "Gear Studio could not start.\n\n" + traceback.format_exc(), "Gear Studio"
        )


def stop(context):
    global _controller
    if _controller is not None:
        try:
            _controller.stop()
        finally:
            _controller = None
