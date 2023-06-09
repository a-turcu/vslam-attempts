from __future__ import print_function

import numpy as np
import signal
import sys
import json

from benchbot_api import ActionResult, Agent
from benchbot_api.tools import ObservationVisualiser
from mmdet3d.apis import init_model

from detection import detect, create_result
from registration import combine_PCD, load_pcd_pipeline
from utils_pcd import open3d_to_numpy, transform_pcd
from const import *


class InteractiveAgent(Agent):

    def __init__(self):
        self.vis = ObservationVisualiser()
        self.step_count = 0
        self.combined_pcd = None
        self.model = init_model(CONFIG_FILE, CHECKPOINT_FILE)

        with open("solution/action_list_miniroom1.txt", 'r') as f:
            self.actions = f.readlines()

        signal.signal(signal.SIGINT, self._die_gracefully)

    def _die_gracefully(self):
        print("Done!")
        sys.exit(0)

    def is_done(self, action_result):
        # Go forever as long as we have a action_result of SUCCESS
        return action_result != ActionResult.SUCCESS

    def pick_action(self, observations, action_list):
        # Perform a sanity check to confirm we have valid actions available
        new_pcd = load_pcd_pipeline('', observations, mode='live')
        if self.step_count == 0:
            self.combined_pcd = new_pcd
        else:
            self.combined_pcd = combine_PCD(self.combined_pcd, new_pcd)

        if ('move_distance' not in action_list or
                'move_angle' not in action_list):
            raise ValueError(
                "We don't have any usable actions. Is BenchBot running in the "
                "right mode (active), or should it have exited (collided / "
                "finished)?")

        # Update the visualisation
        self.vis.visualise(observations, self.step_count)
        print("Step: ", self.step_count)
        if self.step_count == len(self.actions):
            pcd = open3d_to_numpy(self.combined_pcd)
            pcd = transform_pcd(pcd)
            pcd_path = 'live_pcd.npy'
            np.save(pcd_path, pcd)
            results = detect(self.model, pcd_path)
            result_json = create_result(results, threshold=0.7)
            with open("result.json", "w") as f:
                json.dump(result_json, f)


        action = None
        action_args = None
        while (action is None):
            try:
                print(
                    "Enter next action (either 'd <distance_in_metres>'"
                    " or 'a <angle_in_degrees>'): ",
                    end='')
                sys.stdout.flush()

                if self.step_count < len(self.actions):
                    action_text = self.actions[self.step_count].split(" ")
                else:
                    self._die_gracefully()
                    return

                if action_text[0] == 'a':
                    action = 'move_angle'
                    action_args = {
                        'angle': (0 if len(action_text) == 1 else float(
                            action_text[1]))
                    }
                elif action_text[0] == 'd':
                    action = 'move_distance'
                    action_args = {
                        'distance':
                            0
                            if len(action_text) == 1 else float(action_text[1])
                    }
                else:
                    raise ValueError()
            except Exception as e:
                print(e)
                print("ERROR: Invalid selection")
                action = None
        self.step_count += 1

        return (action, action_args)

    def save_result(self, filename, empty_results, results_format_fns):
        return
