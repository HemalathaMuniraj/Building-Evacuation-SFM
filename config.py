"""Global configuration. All physics is in SI units (metres, seconds, kg, N)."""

# --- rendering -------------------------------------------------------------
PX_PER_M = 50.0                 # 1 metre = 50 pixels  (14 m x 9 m room = 700 x 450 px)
WINDOW_SIZE = (1150, 700)
ROOM_ORIGIN_PX = (100, 100)     # top-left corner of the room on screen
FPS = 60

# --- simulation ------------------------------------------------------------
DT = 0.01                       # fixed physics time step [s]
T_MAX = 600.0                   # abort a run that has not finished after this long [s]
SAMPLE_DT = 0.25                # how often metrics are sampled [s]
DISCOVERY_RADIUS = 1.5          # an agent notices a blocked door within this distance [m]
EXIT_CLEARANCE = 0.35           # agent counts as evacuated this far beyond the door line [m]

# --- reference values used for validation -----------------------------------
REFERENCE_SPECIFIC_FLOW = 1.3   # persons / m / s, lower end of published bottleneck-flow values
REFERENCE_FLOW_BAND = (1.3, 1.9)  # approx. range reported in door/bottleneck experiments (verify citations before publishing)