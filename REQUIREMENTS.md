# COMET requirements

This document defines why COMET exists and what it needs to do. It does not describe how COMET is built: libraries, code structure and algorithms belong in design documents.

## Why COMET exists

QRET's test analysis is spread across individual scripts, and our simulations are not connected to test data. Results are hard to reproduce, and work is often lost when members leave. Parameters measured in tests are copied into simulations by hand.

COMET is a shared tool. It turns test data into performance metrics, estimates motor parameters from them, and uses those parameters to simulate motor performance. Test results feed directly into the simulation, and simulation results can be checked against test data.

## Scope

**In scope:** self-pressurizing N2O hybrid motors, cold flow and hotfire tests, data from the Launch Control system.

**Out of scope:** live display during tests, flight trajectory simulation, other propulsion types.

## Requirements

### Data

- **DATA-1** Ingest Launch Control test data, and support new data formats without changes to existing analyses.
- **DATA-2** Define each test's sensor configuration (sensors, units, calibration) without code changes.
- **DATA-3** Never modify original raw data.
- **DATA-4** Flag data quality problems (dropouts, saturation, dead sensors) and never silently produce results from bad data.
- **DATA-5** Provide configurable filtering that keeps the raw signal available and does not shift event timing.
- **DATA-6** Store tests, results and simulations as plain files, so they can be shared through the team's existing file storage.

### Analysis

- **ANA-1** Detect test regions and events (burn, cold flow, liquid-to-vapor transition, valve actuation, ignition), with manual override.
- **ANA-2** Calculate cold flow metrics: oxidizer mass flow, injector pressure drop, injector discharge coefficient and feed system losses, for both N2O and CO2.
- **ANA-3** Calculate hotfire metrics: thrust curve, total impulse (including liquid/vapor phase split), burn time, chamber pressure, oxidizer mass flow, O/F, specific impulse and c* efficiency.
- **ANA-4** Estimate motor model parameters from test data, and output them in a form the simulation can load directly, without re-entering values by hand.
- **ANA-5** Calculate metrics according to documented definitions agreed by the Motor subteam.

### Simulation

- **SIM-1** Simulate the transient performance of a self-pressurizing N2O hybrid motor from initial tank conditions to end of burn.
- **SIM-2** Support SPI, HEM and Dyer injector models.
- **SIM-3** Support circular-port grains and arbitrary 2D port geometries imported from CAD.
- **SIM-4** Reproduce a test's measured chamber pressure, oxidizer mass, and thrust within 10% when using parameters estimated from that test.
- **SIM-5** Match HRAP and the current simulation within 5% when using equivalent models.
- **SIM-6** Report why a simulation ended, and warn when a model is used outside its valid range.
- **SIM-7** Compare simulation results against test data.
- **SIM-8** Export motor data for use in OpenRocket and RocketPy flight simulations.
- **SIM-9** Output heat ratios, mass flow rate, and other parameters useful in motor component design

### Usage

- **USE-1** Be available as a GUI, CLI and Python package, producing the same results from each.
- **USE-2** Produce a standard post-test report within 30 minutes of receiving test data.
- **USE-3** Export results in open formats readable without COMET.
- **USE-4** Accept and display values in SI and US customary units.
- **USE-5** Allow new analysis methods and models to be added without modifying existing ones.
- **USE-6** Make every result reproducible, recording the data, methods, settings and COMET version used.
- **USE-7** Run on Windows, macOS and Linux.
- **USE-8** Be fully usable offline.
