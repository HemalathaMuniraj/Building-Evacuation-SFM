# Building Evacuation Simulation using the Social Force Model (SFM)

**Project:** HTX Building Digital Twin  
**Implementation:** Social Force Model (SFM)  
**Language:** Python  
**Visualization:** Pygame

## 1. Project Overview

This project develops a pedestrian evacuation simulation using the Social Force Model (SFM) to study human movement and evacuation behaviour during emergency situations.

The simulation represents pedestrians as individual agents who move towards available emergency exits while interacting with other pedestrians, walls and obstacles.

The current implementation provides a configurable single-room evacuation environment with multiple scenarios, pedestrian navigation, evacuation metrics and a real-time visualization dashboard.

This implementation serves as an initial simulation prototype towards the broader Building Digital Twin and multi-floor evacuation research objectives.

## 2. Objectives

- Implement pedestrian movement using the Social Force Model.
- Simulate interactions between pedestrians and surrounding obstacles.
- Study evacuation behaviour under different emergency conditions.
- Model exit blockage and alternative evacuation routes.
- Measure evacuation time, pedestrian density and exit flow.
- Compare evacuation outcomes across different scenarios.
- Provide visual and numerical simulation results.

## 3. Social Force Model

The Social Force Model describes pedestrian movement through the combination of different forces.

The implementation considers:

- **Driving force:** Encourages pedestrians to move towards their desired destinations.
- **Pedestrian interaction force:** Models repulsion between nearby pedestrians.
- **Wall and obstacle interaction:** Models pedestrian interaction with room boundaries and obstacles.
- **Body compression force:** Represents physical contact when pedestrians overlap.
- **Sliding friction force:** Represents friction during physical contact.

The model uses a numerical simulation approach with configurable parameters such as relaxation time, interaction strengths and desired pedestrian speed.

## 4. System Architecture

The project is organised into modular Python files.

| File | Responsibility |
|---|---|
| `config.py` | Simulation and rendering configuration |
| `dashboard.py` | Real-time evacuation dashboard |
| `evacuation.py` | Main simulation viewer and user interaction |
| `geometry.py` | Room geometry, exits, walls and obstacles |
| `metrics.py` | Evacuation metrics and CSV export |
| `navigation.py` | Navigation fields and route directions |
| `scenarios.py` | Evacuation scenario definitions |
| `sfm_model.py` | Social Force Model calculations |
| `simulation.py` | Headless evacuation simulation engine |

## 5. Implemented Evacuation Scenarios

The current prototype includes seven scenarios:

1. **Normal Evacuation:** Pedestrians evacuate through one available exit.
2. **Blocked Exit:** The main exit is blocked, requiring pedestrians to discover and use an alternative exit.
3. **Late Blockage:** The main exit becomes blocked after evacuation has started.
4. **High Density:** A larger number of pedestrians evacuate through a single exit.
5. **Two Exits:** Pedestrians select between two available exits.
6. **Pillar at Exit:** An obstacle is placed near the exit to study its effect on pedestrian movement.
7. **Urgent Movement:** Pedestrians move with increased desired speed and no reaction delay.

## 6. Technologies Used

- Python
- NumPy
- Pygame
- Social Force Model
- CSV for simulation result exports

## 7. Project Structure

```text
Building-Evacuation-SFM/
│
├── config.py
├── dashboard.py
├── evacuation.py
├── geometry.py
├── metrics.py
├── navigation.py
├── scenarios.py
├── sfm_model.py
├── simulation.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

## 8. Installation and Execution

### Prerequisites

- Python 3.12 recommended
- pip package manager

### Step 1: Clone the repository

```bash
git clone https://github.com/HemalathaMuniraj/Building-Evacuation-SFM.git
```

### Step 2: Navigate to the project folder

```bash
cd Building-Evacuation-SFM
```

### Step 3: Create a virtual environment

```bash
python -m venv venv
```

### Step 4: Activate the environment

Windows PowerShell:

```bash
.\venv\Scripts\Activate.ps1
```

### Step 5: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Run the simulation

```bash
python evacuation.py
```

To run a particular scenario:

```bash
python evacuation.py --scenario "Two Exits" --seed 3
```

## 9. Simulation Controls

| Key | Function |
|---|---|
| 1–7 | Select evacuation scenario |
| R | Restart simulation |
| SPACE | Pause or resume |
| + / - | Increase or decrease simulation speed |
| H | Toggle heatmap |
| C | Switch colour mode |
| S | Save screenshot |
| E | Export simulation results |
| ESC | Exit simulation |

## 10. Simulation Outputs and Metrics

The simulation dashboard provides information such as:

- Total number of pedestrians.
- Number of evacuated pedestrians.
- Number of remaining pedestrians.
- Simulation time.
- Evacuation progress percentage.
- Evacuation curve.
- Peak pedestrian density.
- Exit flow and evacuation statistics.

The simulation can export results as CSV files, including:

- Summary metrics.
- Individual pedestrian evacuation records.
- Evacuation progress over time.

## 11. Current Implementation Status

The current implementation includes:

- Modular Python simulation architecture.
- Social Force Model with pedestrian interaction and contact forces.
- Room geometry, exits and pillar obstacles.
- Pedestrian navigation and exit selection.
- Seven configurable evacuation scenarios.
- Real-time Pygame visualization.
- Evacuation dashboard and performance metrics.
- CSV-based result export.

## 12. Current Limitations

The current prototype focuses on a single-room evacuation environment.

The following capabilities are not yet implemented:

- Multi-floor building representation.
- Inter-floor connectivity through staircases.
- Building data ingestion pipeline.
- Automated building model validation.
- Integration with the FDDE Toolkit.
- Agent-ready simulation API.

## 13. Future Work

The planned development directions include:

1. Extend the simulation to multi-floor building environments.
2. Model staircases and shared evacuation routes between floors.
3. Develop reusable building data ingestion and validation capabilities.
4. Support multiple occupancy distributions and evacuation scenarios.
5. Improve scenario comparison and result analysis.
6. Develop documented operations for AI agent interaction.
7. Integrate the module with the FDDE Toolkit.

## 14. Project Context

This work contributes to the broader SUTD Building Digital Twin research initiative, which aims to develop reusable building data and evacuation simulation capabilities for integration into the FDDE Toolkit.

The current Social Force Model implementation is an initial simulation prototype and a foundation for further development.

---

**Repository:** https://github.com/HemalathaMuniraj/Building-Evacuation-SFM
**Documentation status:** Initial Social Force Model implementation and project documentation.
