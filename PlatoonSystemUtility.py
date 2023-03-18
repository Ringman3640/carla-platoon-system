# PlatoonSystemUtility
# Provides utility classes for Carla platooning system.
# Author: Franz Alarcon

import json
import time
import numpy
import argparse

import carla
from PlatoonNetworkClient import *

# CarlaConnection
# Static class for connecting to the Carla server.
# To use, call CarlaConnection().connect().
# client, world, and blueprint library accessible through the static members.
class CarlaConnection:
    argparser = argparse.ArgumentParser(
        description=__doc__)
    argparser.add_argument(
        '--host',
        metavar='H',
        default='127.0.0.1',
        help='IP of the host server (default: 127.0.0.1)')
    argparser.add_argument(
        '-p', '--port',
        metavar='P',
        default=2000,
        type=int,
        help='TCP port to listen to (default: 2000)')
    args = argparser.parse_args()

    client = None
    world = None
    bp_lib = None

    # Connect to the Carla server.
    @staticmethod
    def connect():
        CarlaConnection.client = carla.Client(
            CarlaConnection.args.host, 
            CarlaConnection.args.port)
        CarlaConnection.client.set_timeout(2.0)
        CarlaConnection.world = CarlaConnection.client.get_world()
        CarlaConnection.bp_lib = CarlaConnection.world.get_blueprint_library()

# VehicleSpawner
# Class for spawing Carla vechiles in a platoon formation.
# By default, spawns the Toyota Prius Carla model.
# Requires a reference to the carla.world object on creation.
# Intended for use in Carla Map 6.
class VehicleSpawner:
    def __init__(self, carla_world):
        self.carla_world = carla_world
        self.vehicle_name = 'vehicle.toyota.prius'
        self.vehicle = None
        self.vehicle_rank = None
        self.radar = None
        self.default_x_position = -20
        self.default_y_position = -15
        self.default_z_position = 0.1
        self.x_spawn_offset = 7
    
    # Spawn a vehicle in the Carla simulated world.
    # Spawns the vehicle at the coordinate defined by the default position
    #   value member data. 
    # The distance in meters between the center points of each vehicle is
    #   defined by self.x_spawn_offset.
    # On success, the vehicle will be spawned in the Carla world and 
    #   self.vehicle_rank will contain the position of the vehicle within the
    #   platoon (rank 0 is the lead vehicle).
    def spawn_vehicle(self):
        self.vehicle_rank = 0
        spawned = False
        spawn_x_pos = self.default_x_position
        bp_lib = self.carla_world.get_blueprint_library()
        bp = bp_lib.find(self.vehicle_name)
        spawn_rot = carla.Rotation(pitch=0.0, yaw=0.0, roll=0.000000)
        while not spawned:
            try:
                spawn_pos = carla.Location(
                    x=spawn_x_pos,
                    y=self.default_y_position,
                    z=self.default_z_position)
                spawnPoint = carla.Transform(spawn_pos, spawn_rot)
                self.vehicle = self.carla_world.spawn_actor(bp, spawnPoint)
                spawned = True
            except:
                self.vehicle_rank += 1
                spawn_x_pos -= self.x_spawn_offset
        
        if spawn_x_pos == self.default_x_position:
            self.is_lead_vehicle = True

# VehicleRadar
# Wrapper class for the Carla radar sensor.
# Spawns a radar sensor on a target vehicle and allows abstracted data
#   collection from the sensor.
class VehicleRadar:
    def __init__(self):
        self.radar = None
        self.latest_data = None
    
    def spawn_radar(self, vehicle, world):
        bp_lib = world.get_blueprint_library()
        radar_bp = bp_lib.find('sensor.other.radar')
        radar_bp.set_attribute('vertical_fov', '1')
        radar_bp.set_attribute('range', '30')
        radar_pos = carla.Transform(carla.Location(z=0.7, x=2))
        self.radar = world.spawn_actor(radar_bp, radar_pos, attach_to=vehicle, 
                                       attachment_type=carla.AttachmentType.Rigid)
        self.radar.listen(lambda data: self._radar_listener(data))

    # Get the clostest distance detected by the radar.
    # Returns a float of the shortest distance if found.
    # Returns 999 if not distance was detected.
    def get_closest_dist(self):
        if (self.latest_data == None):
            return 999

        points = numpy.frombuffer(self.latest_data.raw_data, 
                                  dtype=numpy.dtype('f4'))
        points = numpy.reshape(points, (len(self.latest_data), 4))

        # points array format is [vel, azimuth, altitude, depth] from numpy
        min_dist = 999
        for point in points:
            if (point[3] < min_dist):
                min_dist = point[3]
            
        return min_dist
    
    # Get the velocity of the detected object relative to the radar sensor.
    # A positive velocity indicates that the object is moving away form the
    #   sensor while a negative velocity indicates the object is moving towards
    #   the sensor.
    # Returns a float of the relative velocity.
    # Returns 999 if there was not detected object.
    def get_relative_velocity(self):
        if (self.latest_data == None):
            return 999

        points = numpy.frombuffer(self.latest_data.raw_data, dtype=numpy.dtype('f4'))
        points = numpy.reshape(points, (len(self.latest_data), 4))

        if (len(points) <= 0):
            return 999

        # points array format is [vel, azimuth, altitude, depth] from numpy
        min_point = points[0]
        for point in points:
            if (point[3] < min_point[3]):
                min_point = point
            
        return min_point[0]

    def _radar_listener(self, radar_data):
        self.latest_data = radar_data

# PlatoonLeadVehicle
# Behavior controller for the lead vehicle in the platoon system.
# Creates a connection to the platoon network and allows control of the lead
#   vehicle using a numbered set of pre-made paths. 
class PlatoonLeadVehicle:
    def __init__(self, vehicle):
        self._vehicle = vehicle
        self._connection = PlatoonNetworkClient()
        self._connection.set_message_handler(self._msg_handler)
    
    # Connect the vehicle to the platoon network.
    def connect(self):
        self._connection.connect()

    # Send important information from a carla.VehicleControl object to other
    #   vehicles in the platoon network.
    def send_vehicle_control_data(self, control: carla.VehicleControl):
        data_json = {
            'messageType': 'controlData',
            'timestamp': time.time(),
            'rank': 0,
            'throttle': control.throttle,
            'brake': control.brake
        }

        self._connection.send(json.dumps(data_json))

    # Execute a selected movement path that controls the lead vehicle. 
    # List of supported movement paths:
    #   1. Throttle, cruise, soft brake
    #   2. Throttle, soft brake
    #   3. Throttle, cruise, soft brake
    #   4. Throttle, soft brake
    #   5. Throttle, cruise (no broadcast), brake
    #   6. Throttle, cruise, brake (no broadcast)
    #   7. Throttle, brake (no broadcast)
    #   8. Slow acceleration
    #   9. Repeated braking
    # No broadcast indicates that the specific action will not be notified
    #   to the platoon network (tests for behavior if a message fails to send).
    def execute_path(self, path_num):
        control = carla.VehicleControl()

        #   1. Throttle, cruise, soft brake
        if (path_num == 1):
            print('Throttle on')
            control.throttle = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(10)
            print('Throttle off')
            control.throttle = 0
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(6)
            print('Soft brake on')
            control.brake = 0.3
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(6)
            return True
        
        #   2. Throttle, soft brake
        elif (path_num == 2):
            print('Throttle on')
            control.throttle = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(10)
            print('Soft brake on')
            control.brake = 0.3
            control.throttle = 0
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(8)
            return True
        
        #   3. Throttle, cruise, soft brake
        elif (path_num == 3):
            print('Throttle on')
            control.throttle = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(10)
            print('Throttle off')
            control.throttle = 0
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(6)
            print('Hard brake on')
            control.brake = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(6)
            return True
        
        #   4. Throttle, soft brake
        elif (path_num == 4):
            print('Throttle on')
            control.throttle = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(10)
            print('Hard brake on')
            control.brake = 1
            control.throttle = 0
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(8)
            return True
        
        #   5. Throttle, cruise (no broadcast), brake
        elif (path_num == 5):
            print('Throttle on')
            control.throttle = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(10)
            print('Throttle off (no broadcast)')
            control.throttle = 0
            self._vehicle.apply_control(control)
            time.sleep(6)
            print('Brake on')
            control.brake = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(6)
            return True
        
        #   6. Throttle, cruise, brake (no broadcast)
        elif (path_num == 6):
            print('Throttle on')
            control.throttle = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(10)
            print('Throttle off')
            control.throttle = 0
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(6)
            print('Brake on (no broadcast)')
            control.brake = 1
            self._vehicle.apply_control(control)
            time.sleep(6)
            return True
        
        #   7. Throttle, brake (no broadcast)
        elif (path_num == 7):
            print('Throttle on')
            control.throttle = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(10)
            print('Brake on (no broadcast)')
            control.brake = 1
            control.throttle = 0
            self._vehicle.apply_control(control)
            time.sleep(8)
            return True
        
        #   8. Slow acceleration
        elif (path_num == 8):
            for i in range(20):
                control.throttle += 0.05
                print('Throttle on {}'.format(control.throttle))
                self._vehicle.apply_control(control)
                self.send_vehicle_control_data(control)
                time.sleep(0.2)
            time.sleep(6)
            print('Brake on')
            control.brake = 1
            control.throttle = 0
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            return True
        
        #   9. Repeated braking
        elif (path_num == 9):
            print('Throttle on')
            control.throttle = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            time.sleep(6)
            for i in range(5):
                print('Brake on')
                control.throttle = 0
                control.brake = 1
                self._vehicle.apply_control(control)
                self.send_vehicle_control_data(control)
                time.sleep(0.3)
                print('Throttle on')
                control.throttle = 1
                control.brake = 0
                self._vehicle.apply_control(control)
                self.send_vehicle_control_data(control)
                time.sleep(1)
            print('Brake on')
            control.throttle = 0
            control.brake = 1
            self._vehicle.apply_control(control)
            self.send_vehicle_control_data(control)
            return True
        else:
            return False

    def _msg_handler(self, msg):
        return

# PlatoonVehicleState
# Enumerators that describe the vehicle state within the platoon.
class PlatoonVehicleState():
    FULL_STOP = 1       # Applying full brakes (emergency stop)
    ADJUST_BACK = 2     # Decelerating 
    ADJUST_FORWARD = 3  # Accelerating
    MAINTAIN = 4        # Replicate controls

# PlatoonVehicleStatus
# Defines the status of a vehicle based on important metricts regarding
#   its throttle, brake, and speed.
class PlatoonVehicleStatus:
    def __init__(self):
        self.state = PlatoonVehicleState.MAINTAIN
        self.timestamp = 0
        self.throttle = 0
        self.brake = 0

# PlatoonFollowerVehicle
# Behavior controller for a following vehicle in the platoon system.
# Creates a connection to the platoon network and controls the behavior of the
#   following vehicle automatically. 
class PlatoonFollowerVehicle:
    def __init__(self, vehicle, rank, world):
        self.vehicle = vehicle
        self.rank = rank

        # State distance ranges
        self.min_safe_dist = 1.5
        self.min_targ_dist = 2.5
        self.max_targ_dist = 3
        # From these values, target range is between 2.5 and 3 meters

        # Maintain speed adjustment range (deadzone)
        self.maintain_speed_deadzone = 1

        self._radar = VehicleRadar()
        self._radar.spawn_radar(vehicle, world)
        self._status = PlatoonVehicleStatus()
        self._lead_status = PlatoonVehicleStatus()
        self._far_front_status = None
        self._close_front_status = None
        self._connection = PlatoonNetworkClient()
        self._connection.set_message_handler(self._msg_handler)

    # Connect to the platoon network
    def connect(self):
        self._connection.connect()

    # Send important information from the follower vehicle's current status to
    #   the platoon network.
    def send_vehicle_status_data(self):
        data_json = {
            'messageType': 'controlData',
            'timestamp': time.time(),
            'rank': self.rank,
            'state': self._status.state,
            'throttle': self._status.throttle,
            'brake': self._status.brake
        }

        self._connection.send(json.dumps(data_json))

    # Update the following vehicle's behavior.
    def update_behavior(self):
        next_status = PlatoonVehicleStatus()
        next_status.state = self.get_next_state()
        strongest_brake = self.get_strongest_brake()

        # Adjust next vehicle status based on state

        if (next_status.state == PlatoonVehicleState.FULL_STOP):
            # FULL_STOP STATE: Apply full brakes and disable throttle
            if (next_status.state != self._status.state):
                print('Status changed to FULL_STOP')
                
            next_status.brake = 1
            next_status.throttle = 0

        elif (next_status.state == PlatoonVehicleState.ADJUST_BACK):
            # ADJUST_BACK STATE: Apply brakes based on distance from forward
            #   vehicle and disable throttle
            # Need to check if vehicles ahead have higher brake values
            if (next_status.state != self._status.state):
                print('Status changed to ADJUST_BACK')

            adjust_strength = self._radar.get_closest_dist() - self.min_safe_dist
            adjust_strength /= self.min_targ_dist - self.min_safe_dist
            adjust_strength = round(adjust_strength * 0.75, 2)

            next_status.brake = max(adjust_strength, strongest_brake)
            next_status.throttle = 0

        elif (next_status.state == PlatoonVehicleState.ADJUST_FORWARD):
            # ADJUST_FORWARD STATE: Apply throttle based on velocity of forward
            #   vehicle and disable brakes unless front platoon is braking
            #   (risk of sling-shotting and causing crash)
            if (next_status.state != self._status.state):
                print('Status changed to ADJUST_FORWARD')

            front_vehicle_status = self.get_front_vehicle_status()
            if (front_vehicle_status.brake == 0):
                adjust_strength = front_vehicle_status.throttle
                speed_diff = self._radar.get_relative_velocity()
                if (speed_diff > 0):
                    adjust_strength += speed_diff
                else:
                    adjust_strength += 0.1
                adjust_strength = round(adjust_strength, 2)

                next_status.brake = 0
                next_status.throttle = adjust_strength
            else:
                next_status.brake = round(front_vehicle_status.brake / 2, 2)
                next_status.throttle = 0
            
        else:
            # MAINTAIN STATE: Copy throttle and brake values of front vehicle
            #   unless another vehicle has a higher priority state
            # Also adjust speed if necessary if the front vehicle is is
            #   approaching or leaving at a significant speed
            if (next_status.state != self._status.state):
                print('Status changed to MAINTAIN')

            target_status = self._lead_status
            if (self._close_front_status != None
                and self._lead_status.state > PlatoonVehicleState.ADJUST_FORWARD):
                target_status = self._close_front_status

            if (self._far_front_status != None
                and self._far_front_status.state > PlatoonVehicleState.ADJUST_FORWARD
                and self._far_front_status.state > target_status.state):
                target_status = self._far_front_status

            next_status.throttle = target_status.throttle
            next_status.brake = target_status.brake

            # I can't tell if this is effective, so im commenting it
            # Seems to make the vehicles more prone to accidents
            # It's supposed to add speed smoothening during MAINTAIN state

            #speed_diff = self._radar.get_relative_velocity()
            #if (speed_diff > self.maintain_speed_deadzone):
            #    if (next_status.throttle > 0):
            #        next_status.throttle += 0.05
            #    else:
            #        next_status.brake -= 0.05
            #else:
            #    if (next_status.throttle > 0):
            #        next_status.throttle -= 0.1
            #    else:
            #        next_status.brake += 0.1
        
        self.update_status(next_status)
    
    # Get the next state that the vehicle should transition to at the current
    #       moment.
    def get_next_state(self):
        dist = self._radar.get_closest_dist()

        if (self._status.state == PlatoonVehicleState.FULL_STOP
            and dist < self.min_safe_dist + 0.2):
            # Keep a buffer so not constantly switching between FULL_STOP and
            #       ADJUST_BACK
            return PlatoonVehicleState.FULL_STOP

        if (dist < self.min_safe_dist):
            return PlatoonVehicleState.FULL_STOP
        if (dist < self.min_targ_dist):
            return PlatoonVehicleState.ADJUST_BACK
        if (dist > self.max_targ_dist):
            return PlatoonVehicleState.ADJUST_FORWARD
        return PlatoonVehicleState.MAINTAIN

    # Update the status of the vehicle and broadcast that update to other
    #   vehicles if changed
    def update_status(self, status: PlatoonVehicleStatus):
        if (status.throttle == self._status.throttle 
            and status.brake == self._status.brake
            and status.state == self._status.state):
            return
        
        control = carla.VehicleControl()
        control.throttle = status.throttle
        control.brake = status.brake

        self.vehicle.apply_control(control)

        self._status = status
        self.send_vehicle_status_data()

    # Get the strongest brake of the tracked vehicles.
    def get_strongest_brake(self):
        brake_val = self._lead_status.brake

        if (self._far_front_status != None 
            and self._far_front_status.brake > brake_val):
            brake_val = self._far_front_status.brake
        if (self._close_front_status != None 
            and self._close_front_status.brake > brake_val):
            brake_val = self._close_front_status.brake

        return brake_val
    
    # Get the current speed of the vehicle.
    def get_speed(self):
        return self.vehicle.get_velocity().length()

    # Get the status of the front vehicle.
    def get_front_vehicle_status(self):
        if (self._close_front_status != None):
            return self._close_front_status
        return self._lead_status

    def _msg_handler(self, msg):
        msg_json = json.loads(msg)
        sender_status = None
        
        if 'rank' not in msg_json:
            return
        
        sender_rank = msg_json['rank']
        if (sender_rank == 0):
            sender_status = self._lead_status
        elif (sender_rank == self.rank - 2):
            if (self._far_front_status == None):
                self._far_front_status = PlatoonVehicleStatus()
            sender_status = self._far_front_status
        elif (sender_rank == self.rank - 1):
            if (self._close_front_status == None):
                self._close_front_status = PlatoonVehicleStatus()
            sender_status = self._close_front_status
        else:
            return
        
        msg_type = msg_json['messageType']
        if (msg_type == 'controlData'):
            sender_status.timestamp = msg_json['timestamp']
            sender_status.throttle = msg_json["throttle"]
            sender_status.brake = msg_json["brake"]
            if (sender_rank != 0):
                sender_status.state = msg_json['state']
