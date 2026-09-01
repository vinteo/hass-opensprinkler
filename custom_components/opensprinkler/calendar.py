import calendar
import logging
from datetime import date, datetime, time, timedelta, timezone
from math import trunc
from zoneinfo import ZoneInfo

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from pyopensprinkler.exceptions import FirmwareNotSupportedError
from suntime import Sun

from .const import (
    DOMAIN,
    SCHEDULE_TYPE_INTERVAL,
    START_TIME_DISABLED,
    START_TIME_SUNRISE,
    START_TIME_SUNSET,
    START_TIME_TYPE_FIXED,
    START_TIME_TYPE_REPEATING,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: dict, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the OpenSprinkler calendar platform."""
    entities = _create_entities(hass, entry)
    async_add_entities(entities)


def _create_entities(hass: HomeAssistant, entry: dict):
    entities = []

    controller = hass.data[DOMAIN][entry.entry_id]["controller"]
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    name = entry.data[CONF_NAME]
    store = Store[dict[date, list[list[any]]]](
        hass, STORAGE_VERSION, f"{DOMAIN}_{name}"
    )

    entities.append(OpenSprinklerCalendar(entry, name, controller, coordinator, store))

    return entities


class OpenSprinklerCalendar(CalendarEntity):
    """Representation of an OpenSprinkler schedule as a calendar."""

    def __init__(self, entry, name, controller, coordinator, store):
        """Initialize the calendar."""
        self._controller = controller
        self.coordinator = coordinator
        self._store = store
        self._attr_name = f"{name} Schedule"
        self._attr_unique_id = f"{entry.unique_id}_calendar"
        self._event = None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming or currently active event."""
        return self._event

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
        find_next_run_only: bool = False,
    ) -> list[CalendarEvent]:
        """Return calendar events within a specific time range."""
        events = []

        predicted_runs = await self._get_runs_for_date_range(
            start_date, end_date, find_next_run_only
        )

        for run in predicted_runs:
            event_start = dt_util.as_utc(run["start_time"])
            event_end = dt_util.as_utc(run["end_time"])

            # Skip runs outside the requested window requested by the UI view
            if not (start_date <= event_start <= end_date):
                continue

            events.append(
                CalendarEvent(
                    summary=f"{run['station_name']}",
                    start=event_start,
                    end=event_end,
                    description=f"{run['program_name']}",
                    location=f"{run['duration']}",
                )
            )

        events.sort(key=lambda x: x.start)
        return events

    async def async_update(self) -> None:
        """Update the entity attributes with next event info."""
        now = dt_util.now()
        a_year = now + timedelta(days=365)

        # Look ahead to find the next active event
        upcoming = await self.async_get_events(
            self.hass, now, a_year, find_next_run_only=True
        )
        if upcoming:
            self._event = upcoming[0]
        else:
            self._event = None

    async def _get_runs_for_date_range(
        self, start_date: datetime, end_date: datetime, find_next_run_only: bool
    ) -> list[dict]:
        """Locate predicted runs for all programs in a date range."""
        runs = []

        if not self._controller.enabled:
            _LOGGER.info("Controller is disabled, no runs will be returned.")
            return runs

        # Adjust search dates to beginning of each local day.
        today = dt_util.start_of_local_day(dt_util.now())
        calendar_day = dt_util.start_of_local_day(start_date)
        last_day = dt_util.start_of_local_day(end_date)

        # If history is being logged, build list of actual historical runs.
        if self._controller.logging_enabled:
            if calendar_day < today:
                end_date = min(today, last_day)
                runs = await self._get_historical_runs_for_date_range(
                    calendar_day, end_date
                )
                calendar_day = end_date

        # Loop through days in the range (after historical runs, if using) and find any programs that can run.
        while calendar_day < last_day:
            programs = self._build_eligible_programs_list(calendar_day)

            # Build the station runs list for the day if there are any runable programs.
            if programs:
                runs += self._build_station_runs_list(programs, today, calendar_day)

            # If we only want the next run, break the while loop and stop collecting runs when we find it.
            # This is a performance optimization to avoid unnecessary calculations for future days when we
            # only need the next run, since we can look a year in the future.
            if find_next_run_only and next(
                (run for run in runs if run["start_time"] > dt_util.now()), None
            ):
                break

            # Otherwise, keep gathering runs
            calendar_day += timedelta(days=1)
        return runs

    def _build_eligible_programs_list(self, calendar_day: datetime) -> list[dict]:
        """Check each program to see if it or its stations can run on this day."""
        programs = []
        for _, _program in self._controller.programs.items():
            if self._can_run_on_day(_program, calendar_day):

                # Program can potentially run. Get its scheduled start times and loop through them.
                program_start_times = self._get_program_start_times(
                    calendar_day, _program
                )

                for program_start_time in program_start_times:

                    # Loop through each station and check if enabled, then add to the stations list
                    stations = self._build_eligible_stations_list(_program)

                    # Add to unordered list of programs for the day if there are any stations enabled.
                    # Also note if any of the stations ignore rain delay, which may be used later.
                    if stations:
                        has_rain_delay_ignored_stations = any(
                            d["rain_delay_ignored"] is True for d in stations
                        )
                        programs.append(
                            {
                                "program_name": _program.name,
                                "start_time": program_start_time,
                                "has_rain_delay_ignored_stations": has_rain_delay_ignored_stations,
                                "stations": stations,
                                "use_weather": _program.use_weather_adjustments,
                                "schedule_type": _program.program_schedule_type,
                                "interval_days": _program.interval_days,
                                "groups": list({d["group"] for d in stations}),
                            }
                        )
        return programs

    def _build_eligible_stations_list(self, program):
        """Check each station to see if it can run on this day and get its details."""
        stations = []
        for _, _station in self._controller.stations.items():
            if _station.enabled:
                duration = program.station_durations[_station.index]
                if duration > 0:

                    # Get group for sequential operations, depending on firmware version
                    group = None
                    try:
                        # Most recent firmware
                        group = _station.group
                    except FirmwareNotSupportedError:
                        # Older firmware, 0->A, 255->P
                        group = 0 if _station.sequential_operation else 255

                    stations.append(
                        {
                            "station_name": _station.name,
                            "duration": int(duration / 60),
                            "rain_delay_ignored": _station.rain_delay_ignored,
                            "group": group,
                        }
                    )
        return stations

    def _can_run_on_day(self, program, check_date: datetime) -> bool:
        """Determine if a program can run on a given date."""
        if not program.enabled:
            return False

        if self._is_restricted_day(program, check_date) or self._is_outside_date_range(
            program, check_date
        ):
            return False
        else:
            match program.program_schedule_type:
                case 0:
                    return self._can_weekly_run_on_day(program, check_date)
                case 1:
                    return self._can_single_run_run_on_day(program, check_date)
                case 2:
                    return self._can_monthly_run_on_day(program, check_date)
                case 3:
                    return self._can_interval_run_on_day(program, check_date)

    def _can_weekly_run_on_day(self, program: dict, check_date: datetime) -> bool:
        """Determine if a weekly program can run on a given date."""
        day_of_week = check_date.strftime("%A")
        return program.get_weekday_enabled(day_of_week)

    def _can_single_run_run_on_day(self, program: dict, check_date: datetime) -> bool:
        """Determine if a Single-run program can run on a given date."""
        epoch = date(1970, 1, 1)
        run_day = epoch + timedelta(days=program.single_run_day)
        return run_day == check_date.date()

    def _can_monthly_run_on_day(self, program: dict, check_date: datetime) -> bool:
        """Determine if a monthly program can run on a given date."""
        run_day = program.monthly_day
        if run_day == 0:  # Last day of month
            year = check_date.year
            month = check_date.month
            _, run_day = calendar.monthrange(year, month)
        return run_day == check_date.day

    def _can_interval_run_on_day(self, program: dict, check_date: datetime) -> bool:
        """Determine if an interval program can run on a given date."""
        interval_days = program.interval_days
        starting_in_days = program.starting_in_days
        next_run_day = dt_util.now() + timedelta(days=starting_in_days)
        difference = (check_date.date() - next_run_day.date()).days
        return difference % interval_days == 0

    def _is_restricted_day(self, program: dict, check_date: datetime) -> bool:
        """Check if Even/Odd Restriction feature would prohibit program from running."""
        if (
            program.odd_even_restriction_name is None
            or program.odd_even_restriction_name == "odd_days"  # odd days only
            and check_date.day % 2 == 1
            and check_date.day != 31
            and not (check_date.month == 2 and check_date.day == 29)
            or program.odd_even_restriction_name == "even_days"  # even days only
            and check_date.day % 2 == 0
        ):
            return False
        else:
            return True

    def _is_outside_date_range(self, program: dict, check_date: datetime) -> bool:
        """Check if Date Range feature would prohibit program from running."""
        if program.date_range_enabled:
            from_day_of_year = self._get_doy_from_date_range_endpoint(
                check_date, program.date_range_from
            )
            to_day_of_year = self._get_doy_from_date_range_endpoint(
                check_date, program.date_range_to
            )
            check_day_of_year = check_date.timetuple().tm_yday

            if from_day_of_year <= to_day_of_year and not (
                from_day_of_year <= check_day_of_year <= to_day_of_year
            ):
                return True
            elif from_day_of_year > to_day_of_year and (
                from_day_of_year > check_day_of_year > to_day_of_year
            ):
                return True
            else:
                return False
        else:
            return False

    def _get_program_start_times(
        self, run_day: datetime, program: dict
    ) -> list[datetime]:
        """Get a start time for a program."""
        start_times = []

        # Get primary start time and any fixed additional start times
        for start_index in range(4):
            minutes = program.get_program_start_time_offset(start_index)
            offset_type = program.get_program_start_time_offset_type(start_index)
            if (
                start_index == 0
                or program.start_time_type_name == START_TIME_TYPE_FIXED
            ):
                if offset_type == START_TIME_SUNRISE:
                    sunrise = self._get_sunrise(run_day)
                    minutes += sunrise.hour * 60 + sunrise.minute
                elif offset_type == START_TIME_SUNSET:
                    sunset = self._get_sunset(run_day)
                    minutes += sunset.hour * 60 + sunset.minute
                elif offset_type == START_TIME_DISABLED:
                    continue  # Program is disabled for this start time

                # Calculate start time and append to the run day
                start_time = time(trunc(minutes / 60), minutes % 60, 0)
                start_times.append(
                    run_day.replace(hour=start_time.hour, minute=start_time.minute)
                )

        # Get repeating times
        if program.start_time_type_name == START_TIME_TYPE_REPEATING:
            for _ in range(program.program_start_repeat_count):
                start_times.append(
                    start_times[len(start_times) - 1]
                    + timedelta(minutes=program.program_start_repeat_interval)
                )

        return start_times

    def _get_doy_from_date_range_endpoint(
        self, check_date: datetime, month_day: list[int]
    ) -> int:
        """Get day of year for a month/day pair and the year of the check_date."""
        return (
            (check_date.replace(month=month_day[0], day=month_day[1]))
            .timetuple()
            .tm_yday
        )

    def _get_sunrise(self, date: datetime) -> datetime:
        """Get sunrise for a given date at the current location."""
        lat = self.hass.config.latitude
        lon = self.hass.config.longitude
        local_tz = self.hass.config.time_zone
        sun = Sun(lat, lon)
        return sun.get_sunrise_time(date).astimezone(ZoneInfo(local_tz))

    def _get_sunset(self, date: datetime) -> datetime:
        """Get sunset for a given date at the current location."""
        lat = self.hass.config.latitude
        lon = self.hass.config.longitude
        local_tz = self.hass.config.time_zone
        sun = Sun(lat, lon)
        return sun.get_sunset_time(date).astimezone(ZoneInfo(local_tz))

    def _epoch_to_local(self, epoch_time: int) -> datetime:
        """Convert local epoch time to local datetime."""
        return datetime.fromtimestamp(epoch_time).astimezone(
            ZoneInfo(self.hass.config.time_zone)
        )

    def _epoch_utc_as_local(self, epoch_seconds: int) -> datetime:
        """Convertr UTC epoch time to local datetime."""
        dt_naive = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).replace(
            tzinfo=None
        )
        local_tz = ZoneInfo(self.hass.config.time_zone)
        return dt_naive.replace(tzinfo=local_tz)

    def _build_station_runs_list(self, programs, today, calendar_day) -> list[dict]:
        """Build ordered list of stations that can run on this day."""
        runs = []

        # Sort the programs by start time
        programs.sort(key=lambda x: x["start_time"])

        # Add programs to the runs list
        station_start_time = programs[0]["start_time"]
        for program in programs:
            original_program_start_time = program["start_time"]
            has_rain_delay_ignored_stations = program["has_rain_delay_ignored_stations"]

            # Append stations to end of last program if schedules overlap.
            # Otherwise start with the program's originally scheduled start time.
            station_start_time = max(station_start_time, original_program_start_time)

            program_qualifies, restrict_to_ignored = (
                self._get_program_final_run_decision(
                    today,
                    calendar_day,
                    original_program_start_time,
                    has_rain_delay_ignored_stations,
                )
            )

            # We'll need to track multiple start times for each station group.
            group_start_times = {}
            for group in program["groups"]:
                group_start_times[group] = {"start_time": station_start_time}

            # If program qualifies to run, append its stations to the runs list.
            runs += self._append_stations_to_run_list(
                program,
                group_start_times,
                calendar_day,
                today,
                program_qualifies,
                restrict_to_ignored,
            )

            # Update the station_start_time to the latest end time of all groups for the next program.
            station_start_time = max(
                [group_start_times[group]["start_time"] for group in program["groups"]]
            )

        return runs

    def _get_program_final_run_decision(
        self,
        today,
        calendar_day,
        original_program_start_time,
        has_rain_delay_ignored_stations,
    ):
        """Check for Weather Restriction, Rain Delay."""
        # Rain delay program selection:
        # Original program start time should be after rain delay stop time;
        # getting bumped past the rain delay stop time by another program's overlapping schedule
        # doesn't qualify the program to run unless it has stations that ignore rain delay.

        # For showing the past during a rain delay, which we don't know when started, we'll not
        # show any runs since midnight.

        # If there is no rain delay, or if there is a rain delay but the program has stations
        # that ignore it, program qualifies.

        # A Weather Restriction blocks all programs for the current day only.

        restrict_to_ignored = False

        if today == calendar_day and self._controller.weather_restriction_active:
            program_qualifies = False
        elif self._controller.rain_delay_active:
            rain_delay_end_time = self._epoch_to_local(
                self._controller.rain_delay_stop_time
            )
            program_time = original_program_start_time

            # Check that start time not inside rain delay time.
            if not (today < program_time < rain_delay_end_time):
                # Program fully qualifies to run.
                program_qualifies = True
            else:
                # Program may partially qualify to run.
                restrict_to_ignored = program_qualifies = (
                    has_rain_delay_ignored_stations
                )
        else:
            # Program fully qualifies to run.
            program_qualifies = True

        return program_qualifies, restrict_to_ignored

    def _append_stations_to_run_list(
        self,
        program,
        group_start_times,
        calendar_day,
        today,
        program_qualifies,
        restrict_to_ignored,
    ):
        """Append a program's qualifying stations to the run list."""
        runs = []
        for station in program["stations"]:
            start_time = group_start_times[station["group"]]["start_time"]
            duration = self.calculate_duration(
                program, station, calendar_day, today, self._controller
            )
            end_time = start_time + timedelta(minutes=duration)

            station_qualifies = False
            if program_qualifies:
                if restrict_to_ignored:
                    station_qualifies = station["rain_delay_ignored"]
                else:
                    station_qualifies = True

            if station_qualifies:
                runs.append(
                    {
                        "program_name": program["program_name"],
                        "station_name": station["station_name"],
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": f"{duration:.0f}m",
                    }
                )

            # Bump start times for all groups except the Parallel group.
            # Whether appending or not, we need to calculate the end time of each station to
            # determine the start time of the next station or program.
            if station["group"] != 255:
                group_start_times[station["group"]]["start_time"] = (
                    end_time + timedelta(seconds=self._controller.station_delay)
                )

        return runs

    def calculate_duration(
        self,
        program: dict,
        station: dict,
        calendar_day: datetime,
        today: datetime,
        controller,
    ):
        """Calculate adjusted duration for a station run."""
        duration = station["duration"]

        # Adjust for weather factor only on current day.
        # Interval programs can use multi-day watering levels if set.
        if program["use_weather"] and calendar_day == today:
            if (
                controller.use_multi_day_watering_levels
                and program["schedule_type"] == SCHEDULE_TYPE_INTERVAL
            ):
                idx = program["interval_days"] - 1
                levels = controller.multi_day_watering_levels
                level = levels[min(idx, len(levels) - 1)] / 100
            else:
                level = controller.water_level / 100

            duration *= level
        return duration

    async def _get_historical_runs_for_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """Locate historical runs for all programs in a date range."""
        # Load cache.
        cached_logs = await self._store.async_load() or {}

        # Attempt to locate logs from cache.
        logs = []
        calendar_day = start_date
        while calendar_day < end_date:
            try:
                day_logs = cached_logs[str(calendar_day.year)][calendar_day.isoformat()]
            except KeyError:
                # Query the controller for missing logs, from missed day to end_date.
                await self._update_cache_from_controller(
                    calendar_day, end_date, cached_logs
                )
                day_logs = cached_logs[str(calendar_day.year)][calendar_day.isoformat()]

            # Copy a day's logs, if any, into the date range list.
            for log in day_logs:
                logs.append(log)
            calendar_day += timedelta(days=1)

        # Save the updated cache.
        await self._store.async_save(cached_logs)

        # Process the logs and return.
        return self._process_logs(logs)

    def _process_logs(self, logs) -> list[dict]:
        """Convert log event to run dict entry."""
        runs = []
        for logged_run in logs:
            program_idx = logged_run[0]
            if program_idx != 0:  # Ignore special events
                station_idx = logged_run[1]
                duration_seconds = logged_run[2]
                end_seconds = logged_run[3]
                program_name = self._get_program_name_from_logs(program_idx)
                stations = self._controller.stations
                station_name = (
                    stations[station_idx].name
                    if station_idx < len(stations)
                    else "<Station Deleted>"
                )
                start_seconds = end_seconds - duration_seconds

                runs.append(
                    {
                        "program_name": program_name,
                        "station_name": station_name,
                        "start_time": self._epoch_utc_as_local(start_seconds),
                        "end_time": self._epoch_utc_as_local(end_seconds),
                        "duration": f"{duration_seconds / 60:.0f}m",
                    }
                )
        return runs

    def _get_program_name_from_logs(self, index) -> str:
        """Lookup program name from 1-based index."""
        match index:
            case 0:
                return "Special Event"
            case 99:
                return "Manual Run"
            case 254:
                return "Run Once"
            case _:
                programs = self._controller.programs
                return (
                    programs[index - 1].name
                    if index <= len(programs)
                    else "<Program Deleted>"
                )

    async def _update_cache_from_controller(
        self, start_date: datetime, end_date: datetime, cached_logs: dict[list]
    ):
        """Query controller for historical runs for all programs in a date range."""
        # Convert times to epoch seconds.
        epoch = dt_util.start_of_local_day(datetime(1970, 1, 1))
        search_start = int((start_date - epoch).total_seconds())
        search_end = int((end_date - epoch).total_seconds())

        # Query controller.
        logs = await self._controller.get_sprinkler_logs(
            start=search_start, end=search_end
        )

        calendar_day = start_date
        log_idx = 0

        # Find all logs in date range.
        while calendar_day < end_date:
            # Find this day's logs.
            day_logs = []
            while log_idx < len(logs):
                log_date = dt_util.start_of_local_day(
                    self._epoch_utc_as_local(logs[log_idx][3])
                )
                if log_date == calendar_day:
                    day_logs.append(logs[log_idx])
                    log_idx += 1
                else:
                    # Logs have moved beyond calendar_day: save to cache and increment day.
                    break

            # Add entry to cache, even if no logs.
            cached_logs.setdefault(str(calendar_day.year), {})[
                calendar_day.isoformat()
            ] = day_logs
            calendar_day += timedelta(days=1)

        # Sort only the years affected (usually just this year).
        for year_int in range(start_date.year, end_date.year + 1):
            cached_logs[str(year_int)] = dict(
                sorted(cached_logs[str(year_int)].items())
            )
