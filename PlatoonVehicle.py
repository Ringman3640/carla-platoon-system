# PlatoonVehicle.py
# Program for spawning a platoon vehicle in the platoon system. 
# The interface for the program changes depending on the type of spawned vehicle
#   (lead vehicle or follower vehicle).
# The Carla server and the platoon network server must both be running.
# Author: Franz Alarcon

import time

from PlatoonSystemUtility import *

# Connect to Carla server
CarlaConnection.connect()
client = CarlaConnection.client
world = CarlaConnection.world

# Spawn vehicle in platoon position
vs = VehicleSpawner(world)
vs.spawn_vehicle()
vehicle = vs.vehicle
platoon_rank = vs.vehicle_rank

try:
    if (platoon_rank == 0):
        print('You are the lead vehicle.')

        vehicle_behavior = PlatoonLeadVehicle(vehicle)
        vehicle_behavior.connect()

        print('Select one of the following path patterns:')
        print('1. Throttle, cruise, soft brake')
        print('2. Throttle, soft brake')
        print('3. Throttle, cruise, soft brake')
        print('4. Throttle, soft brake')
        print('5. Throttle, cruise (no broadcast), brake')
        print('6. Throttle, cruise, brake (no broadcast)')
        print('7. Throttle, brake (no broadcast)')
        print('8. Slow acceleration')
        print('9. Repeated braking')

        path_executed = False
        while not path_executed:
            path_num = input('Enter path number: ')
            path_executed = vehicle_behavior.execute_path(int(path_num))
            if not path_executed:
                print('Unknown path number entered, try again')

    else:
        print("You are vehicle {} in the platoon.".format(platoon_rank + 1))

        vehicle_behavior = PlatoonFollowerVehicle(vehicle, platoon_rank, world)
        vehicle_behavior.connect()

        # Behavior update loop
        # 1 ms pause after each update to prevent platoon network overload
        while True:
            vehicle_behavior.update_behavior()
            time.sleep(0.0001)

finally:
    #print('destroying vehicle')
    #vehicle.destroy()
    print('Path complete')