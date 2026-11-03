# Test data

Real test traces used as fixtures. Values are exactly as exported or published; the
only edits were column renames to the `name_unit` format. Each CSV has a `.yaml`
descriptor next to it naming the channels and their sensor ranges.

**cold-flow-2026-03-06-slice.csv**, QRET cold flow, March 2026, 10 Hz. Three sensors
in it are dead (pre-injector PT, both thermocouples), which the quality checks are
expected to catch. Mean oxidizer flow after despiking is 1.56 kg/s.

**hot-fire-2026-07-11-slice.csv**, QRET HF4, 200 Hz, 29 s around the burn. The main
valve opens at 10015.089 s; liquid depletion is 3.60 s later (from hf_analysis_tools);
7.5 kg of oxidizer used; 15160 N*s total impulse. The load cell is shaken by thrust, so
it is only trusted for before-and-after mass, not for flow.

**mcgill-hf4-2022.csv** and **mcgill-hf5-2022.csv**, McGill Rocket Team Maelstrom
hotfires, extracted exactly from the vector figure in arXiv:2302.06725. Pressures are
absolute (psia). Thrust was plotted on its own time base, so thrust rows carry empty
pressure cells. Time zero is run-valve open; McGill gives liquid depletion at 6.164 s
and 5.272 s, marked where the drop begins. The paper is on arXiv under its
non-exclusive distribution licence; cite it if these numbers are used beyond tests.

**waterloo-stf-2018.csv**, Waterloo Rocketry static fire from their OpenThrustPy repo
(GPL v3), 20 Hz. The source states no units, so psi, kg and N are assumed, and the
chamber pressure channel rises through the burn while thrust falls, so it is not
trusted. No events are published; the oxidizer mass flow collapses at about 10 s.
