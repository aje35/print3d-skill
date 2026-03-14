"""Design session lifecycle management."""

from __future__ import annotations

import os
import tempfile

from print3d_skill.models.create import (
    CreateConfig,
    CreateSession,
    DesignRequest,
)


def create_session(
    request: DesignRequest,
    config: CreateConfig,
    bosl2_available: bool = False,
) -> CreateSession:
    """Create a new design session with a temporary working directory.

    Args:
        request: The user's design specification.
        config: Pipeline configuration with thresholds and options.
        bosl2_available: Whether BOSL2 was detected.

    Returns:
        A new CreateSession ready for iterations.
    """
    working_dir = tempfile.mkdtemp(prefix="print3d_create_")
    return CreateSession(
        request=request,
        config=config,
        working_dir=working_dir,
        bosl2_available=bosl2_available,
    )


def next_iteration_paths(session: CreateSession) -> tuple[str, str, str]:
    """Generate versioned file paths for the next iteration.

    Args:
        session: The active design session.

    Returns:
        Tuple of (scad_path, stl_path, preview_path) for the next iteration.
    """
    version = session.iteration + 1
    base = os.path.join(session.working_dir, f"design_v{version}")
    return (
        f"{base}.scad",
        f"{base}.stl",
        f"{base}_preview.png",
    )


def increment_iteration(session: CreateSession) -> int:
    """Advance the session iteration counter.

    Returns:
        The new iteration number (1-based).
    """
    session.iteration += 1
    return session.iteration
