# Carla Platoon System
A vehicle platooning system demonstration implemented in the [Carla Simulator](https://github.com/carla-simulator/carla).

![Demonstration of the platooning system with six vehicles.](https://github.com/Ringman3640/carla-platoon-system/blob/main/resources/six_platoon_stable.gif)

## Requirements
The platoon system is built on the Carla simulator environment. As such, Carla must be installed to execute the platoon system. All other dependencies are included in the Carla installation process.

## Execution Instructions
The following steps detail the execution process for the platoon system in Carla.

1. Open the Carla simulator in Unreal Engine.

2. Load the "Town 6" map from the content browser in the Unreal Engine viewer.

3. Start the Carla server by clicking "Play" in Unreal Engine.

4. Execute PlatoonNetworkServer.py (required for vehicle communication). 

5. Execute PlatoonVehicle.py to spawn the lead platoon vehicle.

6. Repeat Step 5 to spawn the remaining following platoon vehicles.

7. Select the lead platoon vehicle window and follow the instructions in the console.

For Windows systems, use "open_platoon_vehicles.bat" to automatically execute a select amount of PlatoonVehicle.py scripts.

![Demonstration of using the "open_platoon_vehicles.bat" script to spawn vehicles.](https://github.com/Ringman3640/carla-platoon-system/blob/main/resources/seven_platoon_spawn.gif)

## File Organization
The platoon system is broken into multiple Python scripts.

- **PlatoonNetworkServer.py** - Server program for the platoon network. Hosts vehicle-to-vehicle communication for the whole platoon.

- **PlatoonNetworkClient.py** - Client interface for the platoon network. Allows vehicles to broadcast and recieve messages over the platoon network.

- **PlatonSystemUtility.py** - Utility file that contains the platoon system implementation.

- **PlatoonVehicle.py** - Spawner and manager for an individual platoon vehicle in the platoon system.

- **open_platoon_vehicles.bat** - Batch file to automatically execute a set amount of PlatoonVehicle scripts.
