from base64 import encode
import time
from py_openshowvar import openshowvar

class RemoteControlKUKA:

    def __init__(self, address="192.168.1.15", port=7000, debug=False):
        self.debug = debug
        self._client = openshowvar(address, port)
        if (not self._client.can_connect):
            raise RuntimeError("Unable to connect.")
            
    def __del__(self):
        self._client.close()

    def _read(self, identifier, debug=False):
        return self._client.read(identifier, debug=debug)
        
    def _write(self, identifier, value, debug=False):
        return self._client.write(identifier, value, debug=self.debug or debug)
        
    def get_gripper_states(self):
        gripper_close = self._read("$OUT[1]")
        gripper_open = self._read("$OUT[2]")
        if(gripper_close and not(gripper_open)):
                return "close"     
        elif(gripper_open and not(gripper_close)):
                return "open"
        else:
                return "close"
  
    def get_program_state(self):
        if(self._read("ROBOT_STATES[6]") == b'TRUE'):
            return "home"
        elif(self._read("ROBOT_STATES[5]")== b'TRUE'):
            return "Building tower"
        elif(self._read("ROBOT_STATES[4]") == b'TRUE'):
            return "Calibrating"
        elif(self._read("ROBOT_STATES[3]") == b'TRUE'):
            return "Move to Calibrating area"
        elif(self._read("ROBOT_STATES[2]")== b'TRUE'):
            return "Clamping the target"
        else:
            return "Waiting for connection and data"

    def get_block_x(self):
        block_position = self.transform_coordinate(self._read("DEBUG_E6POS"))
        return block_position['X']

    def get_block_y(self):
        block_position = self.transform_coordinate(self._read("DEBUG_E6POS"))
        return block_position['Y']
      
    def get_block_z(self):
        block_position = self.transform_coordinate(self._read("DEBUG_E6POS"))
        return block_position['Z']

    def get_pos_x(self):
        tool_position = self.transform_coordinate(self._read("$POS_ACT"))
        return tool_position['X']

    def get_pos_y(self):
        tool_position = self.transform_coordinate(self._read("$POS_ACT"))
        return tool_position['Y']
   
    def get_pos_z(self):
        tool_position = self.transform_coordinate(self._read("$POS_ACT"))
        return tool_position['Z']

    def get_level(self):
        return self._read("JENGA_LEVEL").decode('ASCII')
    
    def is_idle(self):
        return b'0' == self._read("COM_ACTION")
        
    def _set_e6pos(self, e6pos):
        self._write("COM_E6POS",e6pos) 
        
    def _set_action(self, s_action):
        if (s_action == "PTP_E6POS"):
            a = 11
        elif (s_action == "LIN_E6POS"):
            a = 12
        else:
            raise NotImplementedError("Unknown action string.")
        self._write("COM_ACTION", str(a))

    def _wait(self, wait=True):
        while (wait and not rck.is_idle()):
            time.sleep(0.1)

    def move_lin_e6pos(self, e6pos, block=True):
        self._set_e6pos(e6pos)
        self._set_action("LIN_E6POS")
        print("here")
        self._wait(block)

    def move_ptp_e6pos(self, e6pos, block=True):
        self._set_e6pos(e6pos)
        self._set_action("PTP_E6POS")
        self._wait(block)

    def transform_coordinate(self,identifier):
        identifier_str = identifier.decode('ascii')
        identifier_parts =identifier_str.strip().strip('{}').split(':')[1].split(',')
        identifier_pairs = [item.strip().split(' ') for item in identifier_parts]
        identifier_pairs = [(k,float(v)) for k,v in identifier_pairs]
        identifier_position = dict(identifier_pairs)
        return identifier_position

if __name__ == '__main__':
    rck = RemoteControlKUKA()
    if True:
        
        gripper_state = rck.get_gripper_states()
      
        program_state = rck.get_program_state()

        tool_pos_x = rck.get_pos_x()
        tool_pos_y = rck.get_pos_y()
        tool_pos_z = rck.get_pos_z()


        block_pos_x = rck.get_block_x()
        block_pos_y = rck.get_block_y()
        block_pos_z = rck.get_block_z()


        
         
        