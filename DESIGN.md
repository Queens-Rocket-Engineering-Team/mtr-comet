# COMET design

This document describes how COMET is built to meet [REQUIREMENTS.md](REQUIREMENTS.md). It covers the overall structure and the main design decisions. Detailed designs for individual parts belong in their own documents or issues. Requirement IDs are given in brackets where a decision exists to meet them.

## Overview

COMET connects test data and simulation:

```text
 test files
     |  ingest
     v
 test Run ---- analysis ----> regions, metrics, report
     |                            |
     |                            v
     |                     motor parameters
     |                            |
     |                            v
     |                    motor configuration
     |                            |  simulation
     |                            v
     +-----> compare <---- simulated Run
                |
                v
           difference [SIM-4, SIM-7]
```

1. **Ingest** reads a test's raw files and its sensor description into a `Run`: a set of measured signals with units.
2. **Analysis** finds the regions of interest (the burn, the liquid phase, valve commands), calculates metrics over them (impulse, Cd, c* efficiency) and produces a report.
3. **Motor parameters** estimated by analysis, such as injector Cd or c* efficiency, are collected into a **motor configuration**.
4. **Simulation** predicts a motor's behaviour from a motor configuration. Its output is also a `Run`, so the same analysis applies to it.
5. **Comparison** of a simulated `Run` against the test it was configured from shows how well the models match reality.

COMET is a Python library. Its code is split into layers (`core`, `ingest`, `models`, `analysis`, `sim`, `api`), described in [Architecture](#architecture). Analysis comes first in implementation.

## Principles

These principles drive the decisions in this document. When a new decision comes up that the document does not cover, make it in line with them.

1. **Every result can be traced and reproduced.** Raw data is never modified, outputs are written once, and every result records how it was made.
2. **The physics exists in one place.** Analysis and simulation share the same models, so a parameter means the same thing in both.
3. **Test and simulation output are the same kind of data.** Both are a `Run`, so any analysis applies to either and they can be compared directly.
4. **Contributing physics does not require software expertise.** Plugins and models are ordinary functions and classes, and COMET handles units, provenance and validation.
5. **The core stays small enough for the next maintainer.** Features are added when something needs them, and every part documents why it exists.
6. **The data outlives the tool.** Plain files, open formats and explicit units keep results readable even if COMET is replaced.

## Terminology

- **Plugin:** a registered implementation of a COMET interface, such as a detector, filter, metric or physical model. Most plugins ship with COMET. A plugin can be replaced by another implementation of the same interface. It does not need to be installed separately.
- **Region:** a closed time interval with a kind and a source. A region may have zero length, or no end if what it marks never completed.
- **Provenance:** the record of what produced a result: the input files, plugins, settings and COMET version.

## Core data model

All parts of COMET share a small set of types defined in `core`.

| Type | Contents |
| --- | --- |
| `Channel` | One signal: name, timestamps, values, unit, kind (continuous or state), metadata (sensor, tags, calibration, source column) and per-sample quality flags. |
| `Run` | A test or a simulation: a set of channels, regions and metadata. Simulation output is a `Run`, so it can be plotted, analyzed and compared with test data in the same way [SIM-7]. |
| `Region` | A time interval with a kind (see [Regions](#regions)), an optional label such as a valve name, and a source: automatic, with the method and settings used, or manual [ANA-1]. |
| `Result` | A scalar with a unit, or a `Channel` for a time series, plus the region it covers, provenance and warnings [USE-6, DATA-4]. |
| `MotorConfig` | Everything the simulation needs: tank, feed, injector, grain, propellants, nozzle and model parameters. Each parameter records where it came from [ANA-4]. |

Decisions:

- Channel values are numpy arrays, so scipy and numpy work on them directly.
- Each channel keeps its own timestamps. Channels are never forced onto a shared time base at ingest, because sensors are sampled at different rates. Resampling and alignment are explicit analysis steps. Channels recorded on the same timestamps share a time base ID, so plugins can combine them without resampling.
- A channel's kind sets how values between samples are read. Continuous channels, such as pressures, are interpolated linearly. State channels, such as valve and relay states, hold their last value until it changes, and carry labels for their values, such as `0: closed, 1: open`. The kind is set in the manifest, not guessed from the data.
- Units are stored with every channel and value. Calculations use SI internally, and conversion happens at input and display [USE-4].
- Configurations are typed, validated when loaded, and saved as plain text. Unknown keys and out-of-range values are errors, not silently ignored.

### Units

- Unit strings such as `853 psig` or `14 in` are parsed with pint. pint is used only at input and display, never inside calculations.
- Gauge and absolute pressure are handled by COMET's own code on plain numbers, not as pint units. pint can only represent a fixed offset, and treating gauge pressure as one would scale the ambient pressure along with a calibration. Calibration is always applied to raw values before any gauge-to-absolute conversion.
- Pressure is gauge at every boundary and absolute inside COMET. All QRET pressure transducers are gauge, so manifests, configurations and settings take gauge values, and reports, plots and the GUI show gauge by default. Inside COMET, pressures are absolute, because fluid properties, CEA and nozzle calculations need absolute pressure.
- QRET does not currently measure ambient pressure. COMET assumes a workspace setting, standard atmosphere by default, which a test's `ambient.pressure` can override. Weather changes atmospheric pressure by about 0.4 psi, which is negligible against tank and chamber pressures. The assumed value is recorded in provenance.
- In files, a pressure level is written with `psig` or `psia`, or with another unit followed by `gauge` or `absolute`, such as `101.3 kPa absolute`. A pressure without a qualifier, such as `40 psi`, is a difference. Temperature levels use `C`, `K` or `F`, and temperature differences use `delta_C` or `delta_K`.
- Plugin and model authors never convert between gauge and absolute. Pressure channels arrive absolute. A setting typed `Pressure` is a pressure level, written in gauge (such as `psig(50)`) and converted to absolute when the plugin runs, using the test's ambient pressure, or the workspace value when there is no test, or standard atmosphere when there is no workspace. A setting typed `PressureDifference`, such as a minimum injector pressure drop, is written as `psi(50)` and is never offset. A metric that returns a pressure declares its unit with the same notation, such as `unit="Pa absolute"` for a level and `unit="Pa"` for a difference, so COMET displays levels in gauge and differences unchanged. Temperature has the same split: `Temperature` for levels and `TemperatureDifference` for differences, such as a temperature rise.
- Files always write units next to values, such as `14 in`, so a change in defaults can never reinterpret old values.

### Standard tags

Plugins find channels by tag instead of by sensor name, so common measurements use a fixed set of tags defined in `core`. Each tag has a physical dimension and a matching input type for plugins.

| Tag | Dimension | Input type | Measurement |
| --- | --- | --- | --- |
| `thrust` | force | `Thrust` | Motor thrust |
| `chamber_pressure` | pressure | `ChamberPressure` | Combustion chamber pressure |
| `tank_pressure` | pressure | `TankPressure` | Oxidizer tank pressure |
| `injector_inlet_pressure` | pressure | `InjectorInletPressure` | Pressure just upstream of the injector |
| `tank_mass` | mass | `TankMass` | Oxidizer tank mass from the load cell |
| `tank_temperature` | temperature | `TankTemperature` | Oxidizer tank temperature |

New standard tags are added to `core` through review. A plugin can use any other tag, but only standard tags have input types. When several channels share a tag, the user chooses one.

Channels without a standard tag, such as pneumatic or supply pressures, are still ingested and can be used by any plugin that takes a plain `Channel` input.

### Regions

- Region kinds have fixed identifiers shared by test and simulation runs: `burn`, `cold_flow`, `ignition`, `liquid_phase`, `vapor_phase` and `valve_command`. Liquid depletion is the boundary between `liquid_phase` and `vapor_phase`. New kinds are added to `core` through review.
- Regions are closed intervals in the run's time, so one region applies to every channel regardless of sample rate.
- Instants, such as a command being sent or a threshold being crossed, are regions of zero length. Processes such as ignition, from igniter fire to sustained combustion, are regions with a duration.
- A region with a start and no end marks something that began but never completed.
- Region operations work in continuous time. Integrals take each channel's value at the region boundaries, averages are weighted by time, and values at an instant are read from the channel, following its kind: interpolated for continuous channels and held for state channels. Results therefore do not depend on where samples happen to fall, and adjacent regions such as the liquid and vapor phases add up exactly.
- A **command region** runs from a command being sent to the control node reporting it, taken from the Launch Control log [ANA-1]. Its duration is the control path latency. A command region with no end means the node never reported. Command regions do not show whether a valve physically moved, because that depends on the plumbing and sensors of a specific setup. Physical response is checked by reviewing command regions against the sensor channels, or with a plugin written for that setup.


## Ingest

- Each data format has an adapter that reads raw files and a test manifest and returns a `Run` [DATA-1]. Adding a format means adding an adapter.
- The manifest is a per-test file describing the sensor configuration [DATA-2]. Algorithms find channels by tag, so changing sensors does not change code.
- Raw files are opened read-only and never rewritten [DATA-3]. They are hashed once, when the test is added, and the hashes are saved in `hashes.yaml` in the test folder for provenance.
- A run's time is the raw data's own timestamps. Adapters never shift, rescale or edit timestamps, so regions saved against a test always match its raw data. Where a clock-sync correction makes time step backward, the samples that overlap earlier times are dropped and flagged. The July 2026 hotfire has four such steps, about 600 s apart, totalling six samples, none during the burn.
- Ingest runs data quality checks (dropouts, saturation, flatlined sensors, timestamp discontinuities) and records them as per-sample quality flags [DATA-4].

### Manifest

```yaml
schema: manifest/1
adapter: lc_csv
time: {source: "device_timestamp", unit: s}
channels:
  PT204:
    source: "PT204 [PSI]"
    unit: psig
    calibration: {scale: 1.0, offset: 0 psi}
    range: [0 psig, 1500 psig]
    tags: [chamber_pressure]
  LCThrust:
    source: "LCThrust [NEWTONS]"
    unit: N
    tags: [thrust]
  AV205:
    source: "valve_AV205"
    kind: state
    labels: {0: closed, 1: open}
```

- `source` is the column or field name in the raw data.
- `kind` is `continuous` (the default) or `state`. State channels can label their values with `labels`.
- `calibration` is linear and is applied to raw values in their own unit, before conversion to SI. Other calibration forms can be added if a sensor needs them.
- `time` names the raw data's time column and its unit.
- `calibration` is optional. Values already converted by the data acquisition system, as in the current Launch Control logs, need none.
- `range` is the sensor's full scale. Values at the upper end are flagged as saturated. The lower end is not flagged, because gauge sensors normally read slightly below zero at rest.
### Test metadata

Each test folder has a `test.yaml` with typed, versioned metadata. Every value carries its unit.

```yaml
schema: test/1
type: hotfire
date: 2026-07-11
motor_config: configs/hf4.yaml
ambient: {pressure: 101.3 kPa absolute, temperature: 24 C}
measurements:
  grain_mass: {before: 1.842 kg, after: 1.311 kg}
  port_diameter: {before: 3.50 in, after: 4.02 in}
  throat_diameter: {before: 42.0 mm, after: 42.6 mm}
notes: ""
```

- `motor_config` points to the motor configuration describing the tested hardware. Plugins that need hardware geometry, such as injector area, read it from there instead of taking it as a setting, so geometry is entered in one place.
- `measurements` holds values measured before and after the test. The hardware changes during a burn: the grain regresses and the nozzle throat erodes. Measured values override the motor configuration's nominal values for that test.
- Each test type defines the measurements it needs. A metric that needs a missing measurement raises an error naming the missing measurement, and the report lists measurements that were not recorded.
- Plugins read metadata as typed fields, such as `run.test.measurements.throat_diameter.before`, so a misspelled field fails immediately.

Metrics that depend on these measurements include:

- c\* efficiency, which interpolates throat area between the before and after diameters
- fuel mass consumed, average O/F and average regression rate, from grain mass and port diameter

### Cache

Parsed test data is not cached: the July 2026 hotfire, about 42 MB of CSV, loads in under a second. Tables that are slow to build, such as CEA combustion tables, are cached in a per-user folder on the local machine, never in the shared workspace, so large cache files do not sync. Each cache entry is keyed by a hash (a fingerprint of the contents) of the inputs it depends on plus the COMET version, so neither a changed input nor changed code reuses a stale entry, and changing injector Cd never rebuilds the CEA tables. The cache can be deleted at any time, and `comet cache clear` empties it.

## Analysis

Analysis is a toolbox of plugins.

Plugin kinds:

- **Filters** produce a new channel from existing channels without reference to any region, such as smoothing, spike removal or resampling. The original channel is untouched. Zero-phase filtering is the default, so event timing does not shift [DATA-5].
- **Detectors** produce regions. Users can override any boundary, and the override is recorded [ANA-1].
- **Metrics** are defined relative to a region and return a scalar or a time series [ANA-2, ANA-3]. Cumulative impulse is a metric that returns a series, and total impulse is its final value.

A **pipeline** is a saved set of plugin steps with their settings. A step can use the outputs of earlier steps, such as a metric computed on a filtered channel, so a pipeline is a small dependency graph. `comet.api` evaluates pipelines incrementally: outputs are kept in memory, keyed by step, settings and inputs (including regions), and changing a setting reruns only that step and the steps that depend on it. Plugin code does not change during a session, so this in-memory cache does not need code versions. Saved pipelines name plugins by registry name.

A result carries a warning when the input samples it used carry quality flags [DATA-4].

### First plugins and standard reports

The first built-in plugins cover the requirements directly:

- **Detectors:** `burn`, `cold_flow`, `liquid_phase` and `vapor_phase`, and `ignition` [ANA-1]. Command regions come from the Launch Control adapter.
- **Metrics:** the cold flow metrics in ANA-2 and the hotfire metrics in ANA-3, each documenting its definition in its docstring as agreed with the Motor subteam [ANA-5].
- **Filters:** zero-phase low-pass and spike removal [DATA-5].

The standard cold flow and hotfire reports are pipelines [USE-2]. A report is a single HTML file with embedded plots, a table of metrics, the regions used and all warnings. It opens offline in any browser and can be printed to PDF. The report's metric values are also exported as CSV [USE-3].

### Writing plugins

Plugin authors range from experienced leads to new members with little software background, so a plugin is an ordinary Python function:

```python
from comet.plugin import metric, Thrust, Region, mean, before, cumulative


@metric(unit="N*s")
def total_impulse(thrust: Thrust, region: Region, baseline_s: float = 0.5) -> float:
    """Total impulse over a region, with thrust zeroed before the region starts.

    Args:
        baseline_s: Length of the window before the region used to zero thrust, in seconds.
    """
    zeroed = thrust.with_values(thrust.values - mean(thrust, before(region, baseline_s)))
    return cumulative(zeroed, region).values[-1]
```

The `@metric` line registers the function with COMET as a metric. The function itself is unchanged.

- **Inputs** are declared by type. Types such as `Thrust` and `ChamberPressure` carry a tag and a physical dimension. A plain `Channel` input lets the user pick the channel, and a `run: Run` input gives access to every channel and the test metadata. Inputs arrive in SI.
- **Settings** are keyword arguments with defaults. Their descriptions come from the docstring. Settings with physical units use dimension types, such as `threshold: Pressure = psig(50)`: the value is SI inside the function, and the GUI shows it in the user's units [USE-4]. A `Literal` setting, such as `method: Literal["threshold", "derivative"]`, becomes a list of fixed choices. A setting that chooses a registered model, such as `model: InjectorModel = "spi"`, becomes a list generated from the registry, so newly added models appear automatically [USE-5].
- **Region helpers** (`mean`, `integrate`, `value_at`, `cumulative`, `before`, `after`) handle region boundaries consistently. Plugins use them instead of slicing arrays, which would give sample-based results that depend on where samples fall.
- **Return values** are plain: a scalar (with its unit in the decorator), a `Channel`, or intervals for a detector. COMET wraps them with provenance and warnings, so plugin code never handles provenance.
- **Plugins stay callable.** A plugin can be called directly in tests and scripts like any Python function.
- **Mistakes are caught early.** Registration checks the function signature and reports problems, such as a missing input type, in plain language.
- Everything a plugin author needs is imported from `comet.plugin`. `comet new metric <name>` creates a plugin file and a test against the July 2026 hotfire. Built-in plugin files are found automatically [USE-5].

### Running plugins

`comet.api` has one function per plugin kind: `detect`, `apply_filter` and `compute`. Each takes a plugin name or the function itself. Separate functions keep the return type of each one clear.

`compute(run, metric, region, inputs=None, **settings)`:

1. Finds the input channels by tag. `inputs` overrides the choice, and missing or ambiguous inputs are an error.
2. Checks input dimensions and converts unit-typed settings to SI.
3. Validates settings against the function signature.
4. Calls the function.
5. Returns a `Result` with the unit, region, warnings and provenance.

### Physics in analysis

Some metrics need the same physics as the simulation: injector Cd from a cold flow needs an injector model and fluid properties, and c\* efficiency needs CEA. These come from `core` and `models`, not from the simulation engine, so analysis can use them without importing `sim`:

- Fluid property and combustion tables are core objects that any plugin can request, such as saturated liquid properties at a pressure. They are built on first use and cached.
- A plugin gets a model by registry name, with settings, through `comet.plugin`.
- Test context reaches plugins through typed `Run` fields: the test metadata, the motor configuration of the tested hardware, the oxidizer or test fluid, and the ambient pressure. Simulated runs provide the same fields from their configuration, so a plugin works on either.

The exact API is settled while building the first cold-flow metric, the first plugin that needs it.

### External plugins

External plugins are planned but are not an early target. They can come from two places:

- **Installed packages** that declare a `comet.plugins` entry point (a standard Python packaging feature that lets an installed package announce plugins) and are installed alongside COMET. Suited to shared, versioned plugins.
- **Workspace plugin files** listed in the workspace's `comet.yaml`. Suited to plugins tied to one test setup. Loading is opt-in because it runs code from shared storage.

Plugin code is the same in both cases, and the same as a built-in plugin. Names are prefixed with the package or file name. The CLI and GUI need one of these routes to find a plugin by name. Python users can pass the function to `comet.api` directly.

Decided now, because they are expensive to change later:

- Built-in and external plugins register through the same API. Built-in plugin modules are imported at startup. External plugin packages are imported when one of their plugins is first named, by a user, a saved pipeline or a motor configuration. A plugin that fails to load is reported and skipped instead of stopping COMET.
- Plugins are identified by registry name, never by Python module path. A registry name is `kind/name`, lowercase with underscores, where `name` is the Python function or class name converted to that form, such as `metric/total_impulse` or `injector/dyer`. External plugins add their package or file name: `metric/qret_teststand.vent_drop_rate`. Where the kind is clear from context, such as `comet.compute` or the `injector` section of a motor configuration, the name alone is enough. Provenance, saved pipelines and motor configurations store registry names, never pickled objects, so moving code between files does not break saved files.
- `comet.plugin` is provisional until the first few real plugins have been written and a newer member has written one from the documentation. After that it is a stable public contract, and changes to it are breaking changes. It starts small, because adding to a public interface is easier than removing from it.
- Provenance records where a plugin came from: package name and version, or the file's hash with a copy of its source in the output folder [USE-6].

## Models

`models` contains the physical models of the motor's components. Both simulation and analysis use them, so the physics exists in one place.

| Component | Variants |
| --- | --- |
| Oxidizer tank | Saturated two-phase tank with vapor-phase blowdown, adiabatic or with wall heat transfer |
| Feed system | Pressure loss |
| Vent (optional) | Vapor flow from the top of the tank through an effective flow area, to atmosphere or into the chamber |
| Injector | SPI, HEM, Dyer [SIM-2] |
| Grain geometry | Circular port, arbitrary 2D port from CAD [SIM-3] |
| Regression | Empirical regression law `a * G_ox^n` per fuel, with fuel blends by volume fraction |
| Combustion | Tables generated with NASA CEA during assembly and cached, with equilibrium or frozen expansion |
| Nozzle | Efficiency losses, choking and separation checks |

Decisions:

- The model kinds in the table are fixed by the hybrid simulation engine, because the engine decides how they connect and what state it tracks. New variants of a kind are plugins. A new kind, such as a pressurant tank, is a change to the engine.
- The vent is an optional kind. It is part of the simulation only when the motor configuration includes a `vent` section, and it is then open for the whole simulation. Its flow leaves the tank's vapor space, so it lowers tank mass and pressure, and when it vents into the chamber its flow is added to the oxidizer entering the chamber.
- Models take the fluid (N2O or CO2) as an input [ANA-2].
- Models are pure functions of their inputs and their configuration: given the same inputs they always return the same result, and calling them changes nothing. Their configuration is fixed once the simulation is assembled. They hold no state and emit no warnings. The engine owns the simulation state, the coupling between models, and valid-range checks. This lets the solver call models at trial values and retry steps safely.
- Tables that models use, such as fluid properties, combustion properties and grain geometry, are core objects, built when first needed, at simulation assembly or by an analysis plugin, and cached. Models read them through the table's lookup method and never build their own interpolators. This lets core change how lookups are computed, for speed, without changing any model.
- Models are written in plain Python. Core may add compiled versions of built-in models, for example with numba, kept next to the plain-Python version and tested to give the same results. Contributors never need to write compiled code.
- Models return a sensible value or raise a typed error for any physically possible input, such as zero flow when chamber pressure exceeds injector inlet pressure.
- Models avoid discontinuities where possible. Real discontinuities, such as liquid depletion, are handled as engine events. The current phase, such as liquid or vapor, reaches models as a field of their input state objects, such as `Inlet.phase`, and a model changes behavior only at an event: a model with an internal switch either smooths it or declares an event for it.
- Flow models are smoothed near zero pressure drop, where a square root has an infinite slope that makes root-finders and the solver struggle. `comet.plugin` provides a smoothed square root for this.

### Writing models

A model is a class registered with the decorator for its kind. The decorator makes it a frozen dataclass: its fields are set once, from the motor configuration, and cannot change afterwards. The fields are the model's settings, following the same rules as plugin settings (defaults, unit types, descriptions from the docstring). The methods are the physics the engine calls.

```python
from math import sqrt
from comet.plugin import injector, Inlet, Area, mm2


@injector
class SPI:
    """Single-phase incompressible injector flow.

    Args:
        cd: Discharge coefficient.
        area: Total injector orifice area.
    """
    cd: float = 0.7
    area: Area = mm2(99)

    def mass_flow(self, inlet: Inlet, p_down: float) -> float:
        dp = inlet.p - p_down
        return self.cd * self.area * sqrt(2 * inlet.rho * dp) if dp > 0 else 0.0

    def check(self, inlet: Inlet, p_down: float) -> str | None:
        if inlet.quality > 0:
            return "SPI used with a two-phase inlet"
        return None
```

- The example uses `sqrt` for readability. A real flow model uses the smoothed square root.
- Each kind has fixed method names, such as `mass_flow` for injectors and `port(web)` for grain geometry. Kinds with state, such as the tank and the grain, also declare named state variables, so a variant with extra state, such as a tank with wall temperature, adds its own without changing the engine.
- Tables a model needs, such as a DXF grain's offset table, are built once with `cached_property`, which computes a value the first time it is used and keeps it.
- The optional `check` method reports when a state is outside the model's valid range. The engine calls it on the recorded output, never on trial states [SIM-6].
- Model modules import heavy libraries such as CoolProp and CEA inside methods or at assembly, so COMET starts quickly.

### Motor configuration

A motor configuration is a YAML file. Each section names a registered model and sets its fields. Values may carry units, which are converted to SI when the file is loaded [USE-4].

```yaml
schema: motor-config/1
engine: hybrid_quasi_steady
propellants: {oxidizer: n2o, fuel: abs}
tank: {model: saturated, volume: 14.6 L, pressure: 853 psig, ullage: 0.045}
injector: {model: dyer, cd: 0.41, area: 99 mm2}
grain: {model: dxf_port, profile: grain/hf4-port.dxf, length: 14 in}
regression: {model: power_law, a: 3.4e-5, n: 0.62}
nozzle: {model: conical, throat_d: 42 mm, exit_d: 95.25 mm}
```

`engine` names the simulation engine, which is registered like a plugin. Today there is one engine, for the self-pressurizing hybrid with a quasi-steady chamber. Another engine, such as one that resolves startup transients or simulates a different motor type, can be added alongside it, with its own model kinds, and existing configurations keep using the engine they name.

Models are found by a lookup in the plugin registry, keyed by kind and name. A configuration can only cause the import of a plugin package that is installed or listed in `comet.yaml`, never arbitrary code. An unknown name produces an error listing the available models.

## Simulation

A simulation runs in the following stages.

1. **Assemble.** Load the motor configuration, construct the models, and build fluid property tables, grain geometry tables and combustion tables. Combustion tables are generated with NASA CEA for the configured propellants and checked against direct CEA calls between grid points. Tables are cached, so repeated runs skip this stage.
2. **Run.** Integrate the motor state over time with scipy's `solve_ivp`, an ODE solver that chooses its own step sizes to meet an accuracy target [SIM-1].

The combustion chamber is treated as quasi-steady. The chamber fills and empties in about a millisecond (its characteristic length divided by c\*), while the tank blows down over seconds. Chamber pressure is therefore not a state variable. At each derivative evaluation, the engine solves for the chamber pressure at which injector flow plus fuel flow equals nozzle flow. This avoids a stiff system that would force the solver into very small steps. The cost is that the first few milliseconds of startup, while the chamber fills, are not resolved.

The chamber balance is its own function, solved with a bracketed root-finder between physical bounds (ambient and tank pressure). It starts from the previous chamber pressure, which the engine keeps, and uses a tolerance tighter than the solver's. Its iterations and any failures are recorded.

The engine builds its state vector at assembly from the named state variables each model declares, and names the output channels from them.

During the run:

- The engine calls `solve_ivp` in short chunks of simulated time, continuing from the end state of the previous chunk. Between chunks it records the solution, reports progress and checks for cancellation, so a cancelled run keeps everything computed so far.
- Transitions such as liquid depletion and fuel depletion are `solve_ivp` events: functions of the state that cross zero when the transition happens. The solver locates them at their exact time. They become regions in the output and give the termination reason [SIM-6].
- At a phase change, such as liquid to vapor, the engine starts a new `solve_ivp` call from the event state, so the solver never steps across a discontinuity.
- Model `check` methods run on the recorded output after integration, so they never see trial states the solver rejected [SIM-6].
- Solver tolerances are set explicitly, per state variable, and recorded in provenance. scipy's default relative tolerance of 1e-3 is too loose for the conservation checks. Solver statistics, such as derivative evaluations, steps and events, are recorded with the root-finder statistics.
- Runs are repeatable: the same configuration gives the same result. An assembled motor can be copied with changed parameters and sent to another process, so parameter fitting and Monte Carlo can be added later without changing the models.

Models are called on every derivative evaluation, several times per step and at trial states the solver may reject, so a burn involves tens of thousands of model calls. The inner loop uses pre-built tables and never calls CoolProp or CEA directly.
Output is a `Run` containing time histories including chamber pressure, thrust, oxidizer and fuel mass flow, O/F, specific heat ratio and the other quantities used in component design [SIM-9]. Its regions, such as `burn`, `liquid_phase` and `vapor_phase`, have the same kinds as regions detected in test data, so analysis plugins run unchanged on simulation output. The run also records the termination reason and diagnostics such as mass and energy conservation checks.

```python
config = comet.load_config("workspace/configs/hf4.yaml")
sim = comet.simulate(config, progress=show_progress, cancel=stop_event)
total = comet.compute(sim.run, "total_impulse", region=sim.run.region("burn"))
```

Exporters write motor data for OpenRocket and RocketPy [SIM-8].

How simulations are checked against HRAP and the current in-house simulation [SIM-5], and how the SIM-4 comparison is measured, are settled in a separate review of this section before simulation work starts.

## Motor parameters from tests

Motor parameters are estimated directly from test data by metric plugins in `analysis`, using the same models as the simulation:

- **Injector Cd** from a cold flow, using measured mass flow and pressure drop. Cd depends on the injector model it was estimated with, so the parameter records the model, and the simulation refuses a Cd estimated under a different model.
- **Feed loss** from a cold flow, using tank and injector inlet pressures and mass flow.
- **c\* efficiency** from a hotfire: measured c\* compared with the CEA value at the measured O/F.
- **Regression coefficients** from grain mass before and after a hotfire. One hotfire gives a single average regression rate, so it can set `a` only with `n` taken from published data for the fuel. Estimating `n` needs several hotfires at different oxidizer fluxes.

`comet.api` collects these results into a motor configuration, written to `configs/` like any other, which the simulation loads directly [ANA-4]. Each parameter records the test and plugin it came from.

Parameters are checked by simulating the test with them and comparing the result with the test `Run` [SIM-4, SIM-7].

Estimating parameters by running the simulation inside a fit is not part of the current design. If it becomes necessary, it will be a new layer above `analysis` and `sim`, so that neither has to import the other.

## Storage

COMET works on a workspace folder of plain files [DATA-6]. The folder can live in any synced location, such as SharePoint.

```text
workspace/
  comet.yaml                        workspace settings
  tests/
    2026-07-11-hotfire/
      raw/                          original files, never modified
      manifest.yaml                 sensor configuration
      test.yaml                     metadata
      regions.yaml                  manual regions and overrides
      hashes.yaml                   raw file hashes, written when the test is added
  results/
    20261029T214500Z-hotfire-report/
      channels.parquet              the run's channels and the channels the analysis computed
      metrics.csv
      regions.yaml                  regions used, detected and manual
      pipeline.yaml                 pipeline and settings that were run
      report.html
      provenance.yaml
  configs/<name>.yaml               motor configurations
  sims/<id>/                        simulation output, same layout as results
```

Decisions:

- Test folders are named with an ISO 8601 date followed by a description, such as `2026-07-11-hotfire`. All dates in COMET use ISO 8601.
- Output folders are named with an ISO 8601 UTC timestamp in basic format followed by a description, such as `20261029T214500Z-hotfire-report`. The basic format has no colons, which Windows does not allow in file names.
- Every analysis or simulation writes a new folder and never overwrites an existing one. This keeps results reproducible and avoids sync conflicts.
- Output folders are self-contained. They include the run's channels, so a folder can be shared or opened without the test folder.
- Output folders are a record of what was computed and reported. COMET never reads them back as inputs. Anything COMET reuses, such as motor parameters estimated from tests, is written as an input file, such as a motor configuration in `configs/`.
- Channel data is stored as one Parquet file per run. Parquet is a compressed table format that pandas, polars and most data tools can read. The table has one row per sample, with columns for channel, time, value and quality flags, and channel units, tags and sources are stored in the file's metadata. This keeps each channel's own timestamps without creating many small files to sync. CSV export is available [USE-3].
- Metadata and configuration are YAML.
- Files a configuration depends on, such as a grain DXF, are copied into the output folder [USE-6].

### Provenance

Each output folder contains `provenance.yaml` [USE-6]:

- `schema`, COMET version, and git commit when COMET runs from a git checkout
- creation time (ISO 8601, UTC)
- inputs: the test folder, with hashes of the raw files, `manifest.yaml`, `test.yaml`, `regions.yaml` and any configuration
- the ambient pressure assumed
- each plugin used: registry name, origin, settings and input channels
- regions used, and whether each was detected or set manually
- for simulations, solver tolerances and statistics
- all warnings

### Manual regions and overrides

Manual regions and boundary overrides are saved in `regions.yaml` in the test folder, not in raw data or in output folders [ANA-1]. The GUI and CLI write it, and it can be edited by hand.

```yaml
schema: regions/1
regions:
  - {kind: burn, start: 10015.18 s, end: 10021.26 s, note: "excluded igniter spike"}
```

Times are in the run's time, which is the raw data's own timestamps. A region in `regions.yaml` replaces detected regions of the same kind and label for that test. Every analysis reads it, and its hash is recorded in provenance, so a result always shows which overrides it used.

### File format versions

File formats will change over time, so every file COMET writes records its format and version:

- Every YAML file has a `schema` field such as `motor-config/2`. Parquet files carry it in their metadata. Each format has its own integer version, independent of the COMET version.
- Upgrades apply to the files COMET reads: manifests, `test.yaml`, `regions.yaml`, motor configurations and saved pipelines. Output folders are never read back, so they are never upgraded. A newer COMET reruns the analysis instead.
- Upgrade code is written at the first breaking change to a format, not before. When it exists, older files are upgraded when read, never rewritten in place, and upgrades only restructure a file, such as renaming or moving fields. They never change values.
- Adding an optional field with a default does not need a new version. Renaming or removing a field, or changing its meaning or unit, does.
- A file written by a newer COMET is refused with a message saying a newer COMET is needed.
- One example file for each version of each format is kept in the repository, and tests load each one.

## Interfaces

- **Python package:** `comet.api`, a small set of functions such as `load_test`, `detect`, `apply_filter`, `compute`, `analyze` (run a pipeline and save its output), `simulate`, `motor_config_from_tests`, `compare` and `export` [USE-1]. Plugin authors use `comet.plugin`.
- **CLI:** a thin wrapper around `comet.api`.
- **GUI:** a PySide6 desktop app wrapping `comet.api`, built after the CLI. Plots use pyqtgraph, which handles large time series and lets users drag region boundaries for manual overrides [ANA-1]. Settings forms are generated from plugin and configuration schemas.
- **GUI analysis sandbox:** besides running the standard pipelines, users can build an analysis interactively: apply filters, detectors and metrics, adjust settings and see results update live, with raw and filtered channels overlaid. Recomputation waits until a setting stops changing, and plots are downsampled for display. The sandbox state is a pipeline, so it can be saved and rerun on other tests. Nothing in the sandbox is a result until it is saved, which writes a normal output folder with provenance. Values quoted in reviews come from the standard pipelines [ANA-5]. The sandbox is a list of steps, not a node editor, and each step owns one output that updates in place. Its state is held in a session object in `comet.api` with no Qt dependency, and the GUI displays that object's changes.

Long-running operations accept progress and cancellation callbacks, so a GUI can show progress without the library knowing about it. A cancelled operation keeps what it computed so far.

### Installation

- Releases are wheels (installable Python packages) attached to GitHub Releases. Version numbers are set manually.
- Users install with uv (`uv tool install <wheel URL>`). uv downloads a suitable Python automatically, so users do not need Python installed.
- Double-click install scripts for Windows, macOS and Linux run the uv install for members who do not use a terminal.
- Standalone app bundles that need no Python or terminal are deferred until the GUI exists.
- Installing needs network access once. After that COMET works offline [USE-8].

## Architecture

COMET's code is split into layers. Each layer depends only on the layers below it.

```text
 cli        gui                     frontends
 api                                use-case functions (comet.api)
 analysis   sim                     test analysis | motor simulation
 ingest     models                  data formats  | physical models
 core                               data types, units, plugin registry
```

Rules:

- Dependencies point downward only. Analysis and simulation do not import each other. They exchange data through motor configurations (see [Motor parameters from tests](#motor-parameters-from-tests)).
- Nothing outside `sim` depends on simulation engine internals. Other layers use only `simulate(config) -> Run` and the model kind interfaces, so an engine can be replaced or added without changes elsewhere.
- Everything below the frontends has no user-facing side effects. It does not print, open plot windows, prompt, or read command line arguments. It returns data and raises typed exceptions. This keeps results identical across interfaces [USE-1].
- The core is kept small, well tested and well documented, including why each part exists. Few people maintain it at any one time, and they change as members graduate. Framework features are added only when something needs them.
- COMET has two public modules: `comet.api` for people using COMET, and `comet.plugin` for people writing plugins. `comet.plugin` gathers the parts of `core` and `models` that plugin authors need. Everything else is internal.
- These rules are checked in CI, the automated checks that run on every pull request. import-linter fails the build on an import across layers or from a frontend into anything other than `comet.api`. ruff bans `print` below the frontends, and ty type-checks the whole package.

## Technology

| Area | Choice |
| --- | --- |
| Language | Python 3.13 or 3.14 (`>=3.13,<3.15`), widened as dependencies publish wheels |
| Numerics | numpy, scipy |
| Configuration and validation | pydantic |
| Units | pint (input and display only) |
| Cache location | platformdirs |
| Fluid properties | CoolProp |
| Combustion equilibrium | NASA CEA (`cea`) |
| CAD geometry | ezdxf, shapely |
| Plotting | matplotlib |
| File formats | pyarrow (Parquet), PyYAML |
| CLI | typer |
| GUI | PySide6 (Qt), pyqtgraph for interactive plots |
| Packaging and tooling | uv (with the `uv_build` backend), ruff, pytest |
| Type checking and layer rules | ty (version pinned), import-linter |

All dependencies must install from wheels on Windows, macOS and Linux and work offline [USE-7, USE-8].

NASA CEA sets the narrowest platform limits. Version 3.3.4 publishes wheels for CPython 3.11 to 3.14, which covers COMET's supported versions, on:

- Windows x86-64
- macOS 14+ on Apple Silicon, and macOS 15+ on Intel
- Linux x86-64 (glibc 2.27+)

Other platforms, such as ARM Linux or older Intel Macs, would need a source build with a Fortran compiler and are not supported.
