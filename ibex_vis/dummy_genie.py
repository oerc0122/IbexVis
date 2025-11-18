"""Fake genie injection."""

import logging
from collections.abc import Callable
from typing import Any
from typing import NoReturn as Never

from ibex_vis.classes import Check, CurrentState, Property

logger = logging.getLogger(__name__)


class Abort(Exception): ...


CURRENT_STATE: CurrentState = CurrentState({}, [], {})


class genie:  # noqa: PLR0904
    @staticmethod
    def begin(*_: Never, **__: Never) -> None:
        if CURRENT_STATE.counting is not None:
            logger.warning("`begin` without `end`")

        CURRENT_STATE.counting = CURRENT_STATE.properties["time"].current

    @staticmethod
    def end(*_: Never, **__: Never) -> None:
        if CURRENT_STATE.counting is None:
            logger.warning("`end` without `begin`")

        CURRENT_STATE.counts.append(
            (CURRENT_STATE.counting, CURRENT_STATE.properties["time"].current),
        )
        CURRENT_STATE.counting = None

    @staticmethod
    def cget(block: str) -> None:
        logger.info(CURRENT_STATE.properties[block].current)

    @staticmethod
    def cset(
        *args: Any,
        runcontrol: bool | None = None,
        lowlimit: float | None = None,
        highlimit: float | None = None,
        wait: bool | None = None,
        verbose: bool | None = None,
        **kwargs: float,
    ) -> None:
        """Sets the setpoint and runcontrol settings for blocks.

        Parameters:
            runcontrol (bool, optional): whether to set runcontrol for this block
            wait (bool, optional): pause execution until setpoint is reached (one block only)
            lowlimit (float, optional): the lower limit for runcontrol or waiting
            highlimit (float, optional): the upper limit for runcontrol or waiting
            verbose (bool, optional): report what the new block state is as a result of the command

        Note:
            cannot use wait and runcontrol in the same command

        Examples:
            Setting a value for a block:

            >>> cset(block1=100)
            Or:

            >>> cset("block1", 100)
            Setting values for more than one block:

            >>> cset(block1=100, block2=200, block3=300)

            NOTE:
            the order in which the values are set is random, e.g. block1 may or may not be set
            before block2 and block3

            Setting runcontrol values for a block:

            >>> cset(block1=100, runcontrol=True, lowlimit=99, highlimit=101)
            Changing runcontrol settings for a block without changing the setpoint:

            >>> cset("block1", runcontrol=False)
            >>> cset(block1=None, runcontrol=False)
            Wait for setpoint to be reached (one block only):

            >>> cset(block1=100, wait=True)
            Wait for limits to be reached - this does NOT change the runcontrol limits:

            >>> cset(block1=100, wait=True, lowlimit=99, highlimit=101)
        """
        if args:
            kwargs |= dict(zip(args[::2], args[1::2], strict=True))

        for key, val in kwargs.items():
            current = CURRENT_STATE.properties[key]
            current.target = val
            current.validrange = (lowlimit, highlimit)
            current.runcontrol = runcontrol

        if wait:
            for item in kwargs.items():
                genie.waitfor(*item)

    @staticmethod
    def change(**params: str | int) -> None:
        """Change experiment parameters.

        Parameters:
            title (string, optional): the new title
            period (int, optional): the new period (must be in a non-running state)
            nperiods (int, optional): the new number of software periods
                (must be in a non-running state)
            user (string, optional): the new user(s) as a comma-separated list
            rb (int, optional): the new RB number

        Notes:
            It is possible to change more than one item at a time.
        """
        CURRENT_STATE.run_variables.update(params)

    @staticmethod
    def change_title(title: str) -> None:
        genie.change(title=title)

    @staticmethod
    def change_rb(rb: int) -> None:
        genie.change(rb=rb)

    @staticmethod
    def change_period(period: int) -> None:
        genie.change(period=period)

    @staticmethod
    def change_users(users: str) -> None:
        genie.change(user=users)

    @staticmethod
    def enable_soft_periods(nperiods: int) -> None:
        genie.change(nperiods=nperiods)

    @staticmethod
    def abort(*_: Never, **__: Never) -> Never:
        raise Abort

    @staticmethod
    def load_script(
        name: str,
        check_script: bool = True,
        warnings_as_error: bool = False,
    ) -> None: ...  # TODO

    @staticmethod
    def pause(
        verbose: bool = False,
        immediate: bool = False,
        prepost: bool = True,
    ) -> None: ...  # TODO

    @staticmethod
    def resume(verbose: bool = False, prepost: bool = False) -> None: ...  # TODO

    @staticmethod
    def waitfor(
        block: str | None = None,
        value: float | None = None,
        lowlimit: float | None = None,
        highlimit: float | None = None,
        maxwait: float | None = None,
        wait_all: bool = False,
        seconds: float | None = None,
        minutes: float | None = None,
        hours: float | None = None,
        time: str | None = None,
        frames: int | None = None,
        raw_frames: int | None = None,
        uamps: float | None = None,
        mevents: float | None = None,
        early_exit: Callable[[], bool] | None = None,
        quiet: bool = False,
        **pars: float,
    ) -> None:
        """Interrupts execution until certain conditions are met.

        Parameters:
            block (string, optional): the name of the block to wait for
            value (float, optional): the block value to wait for
            lowlimit (float, optional): wait for the block to be >= this value (numeric only)
            highlimit (float, optional): wait for the block to be <= this value (numeric only)
            maxwait (float, optional): wait no longer that the specified number of seconds
            wait_all (bool, optional): wait for all conditions to be met
                (e.g. a number of frames and an amount of uamps)
            seconds (float, optional): wait for a specified number of seconds
            minutes (float, optional): wait for a specified number of minutes
            hours (float, optional): wait for a specified number of hours
            time (string, optional): a quicker way of setting hours, minutes and seconds
                (must be of format “HH:MM:SS”)
            frames (int, optional): wait for a total number of good frames to be collected
            raw_frames (int, optional): wait for a total number of raw frames to be collected
            uamps (float, optional): wait for a total number of uamps to be received
            mevents (float, optional): wait for a total number of millions of events to be collected
            early_exit (lambda, optional): stop waiting if the function evaluates to True
            quiet (bool, optional): suppress normal output messages to the console
        """
        if early_exit is not None:
            raise NotImplementedError("Cannot support `early_exit`")

        amps = 0
        events = 0
        curr_time = 0
        frame = 0
        raw_frame = 0

        total_time = None

        stop_check = all if wait_all else any

        if time is not None:
            hours, minutes, seconds = map(float, time.split(":"))

        if any((hours, minutes, seconds)):
            hours = hours or 0
            minutes = minutes or 0
            seconds = seconds or 0
            total_time = hours * 60 + minutes + seconds / 60

        if uamps:
            uamps *= 60

        exit_cond = {}

        if total_time is not None:

            def exit_cond_time() -> bool:
                return curr_time >= total_time

            logger.debug("time: %f", total_time)
            exit_cond["time"] = exit_cond_time
        if uamps is not None:

            def exit_cond_amps() -> bool:
                return amps >= uamps

            logger.debug("amps: %f", uamps)
            exit_cond["amps"] = exit_cond_amps
        if frames is not None:

            def exit_cond_frames() -> bool:
                return frame >= frames

            logger.debug("frames: %d", frames)
            exit_cond["frames"] = exit_cond_frames
        if raw_frames is not None:

            def exit_cond_raw_frames() -> bool:
                return raw_frame >= raw_frames

            logger.debug("raw_frames: %d", raw_frames)
            exit_cond["raw_frames"] = exit_cond_raw_frames
        if mevents is not None:

            def exit_cond_events() -> bool:
                return events >= mevents

            logger.debug("events: %d", mevents)
            exit_cond["events"] = exit_cond_events

        if block is not None and value is not None:
            pars[block] = value

        for blk, val in pars.items():
            if val is not None:
                logger.debug("%s: %d", blk, val)
                exit_cond[blk] = Check(CURRENT_STATE.properties[blk], val)

            if lowlimit is not None or highlimit is not None:
                logger.debug("%s_low: %d", blk, lowlimit)
                logger.debug("%s_high: %d", blk, highlimit)
                exit_cond[f"{blk}_low"] = Check(
                    CURRENT_STATE.properties[blk],
                    (lowlimit, highlimit),
                )

        run_controllers = [prop for prop in CURRENT_STATE.properties.values() if prop.runcontrol]

        while not stop_check(cond() for cond in exit_cond.values()):
            for prop in CURRENT_STATE.properties.values():
                prop.advance()

            curr_time += CURRENT_STATE.properties["time"].current_rate
            raw_frame += 1

            if not run_controllers or all(map(Property.inrange, run_controllers)):
                amps += CURRENT_STATE.properties["beam"].current_rate
                events += CURRENT_STATE.properties["events"].current_rate
                frame += 1

            if maxwait and curr_time >= maxwait:
                break

    @staticmethod
    def waitfor_time(
        seconds: float | None = None,
        minutes: float | None = None,
        hours: float | None = None,
        time: str | None = None,
        quiet: bool = False,
    ) -> None:
        """Interrupts execution for a specified amount of time

        Parameters:
            seconds (float, optional): wait for a specified number of seconds
            minutes (float, optional): wait for a specified number of minutes
            hours (float, optional): wait for a specified number of hours
            time (string, optional): a quicker way of setting hours, minutes and seconds
                                     (must be of format “HH:MM:SS”)
            quiet (bool, optional): suppress normal output messages to the console

        Examples:
            >>> waitfor_time(seconds=10)
            >>> waitfor_time(hours=1, minutes=30, seconds=15)
            >>> waitfor_time(time="1:30:15")
        """
        genie.waitfor(seconds=seconds, minutes=minutes, hours=hours, time=time, quiet=quiet)

    @staticmethod
    def waitfor_uamps(uamps: float, quiet: bool = False) -> None:
        """Interrupts execution to wait for a specific total charge

        Parameters:
            uamps: the charge to wait for
            quiet (bool, optional): suppress normal output messages to the console

        Example:
            >>> waitfor_uamps(115.5)
        """
        genie.waitfor(uamps=uamps, quiet=quiet)

    @staticmethod
    def waitfor_raw_frames(raw_frames: int, quiet: bool = False) -> None:
        """Interrupts execution to wait for number of total raw frames to reach parameter value

        Parameters:
            frames (raw): the number of raw frames to wait for
            quiet (bool, optional): suppress normal output messages to the console

        Example:
            >>> waitfor_raw_frames(4000)
        """
        genie.waitfor(frames=raw_frames, quiet=quiet)

    @staticmethod
    def waitfor_runstate(
        state: str,
        maxwaitsecs: int = 3600,
        onexit: bool = False,
        quiet: bool = False,
    ) -> None:
        """Wait for a particular instrument run state.

        Parameters:
            state (string): the state to wait for (e.g. "paused")
            maxwaitsecs (int, optional): the maximum time to wait for the state before carrying on
            onexit (bool, optional): wait for runstate to change from the specified state
            quiet (bool, optional): suppress normal output messages to the console

        Examples:
            Wait for a run to enter the paused state:

            >>> waitfor_runstate("paused")
            Wait for a run to exit the paused state:
            >>> waitfor_runstate("paused", onexit=True)
        """
        # TODO

    @staticmethod
    def waitfor_move(*blocks: str | None, **kwargs: int | None) -> None:
        """Wait for all motion or specific motion to complete.

        If block names are supplied then it will only wait for those to stop moving. Otherwise,
        it will wait for all motion to stop.

        Parameters:
            blocks (string, multiple, optional): the names of specific blocks to wait for
            start_timeout (int, optional): the number of seconds to wait
                for the movement to begin
                (default = 2 seconds)
            move_timeout (int, optional): the maximum number of seconds
                to wait for motion to stop

        Examples:
            Wait for all motors to stop moving:

            >>> waitfor_move()
            Wait for all motors to stop moving with a timeout of 30 seconds:

            >>> waitfor_move(move_timeout=30)
            Wait for only slit1 and slit2 motors to stop moving:

            >>> waitfor_move("slit1", "slit2")
        """
        # TODO

    @staticmethod
    def waitfor_mevents(mevents: float, quiet: bool = False) -> None:
        """Interrupts execution to wait for number of millions of events to reach parameter value

        Parameters:
            mevents (float): the number of millions of events to wait for
            quiet (bool, optional): suppress normal output messages to the console

        Example:
            >>> waitfor_mevents(0.0004)
        """
        genie.waitfor(mevents=mevents, quiet=quiet)
