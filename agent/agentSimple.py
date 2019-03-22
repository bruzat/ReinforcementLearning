from agent import baseAgent
from pysc2.lib import actions, features
import numpy as np

import agent.log as log

class AgentSimple(baseAgent.BaseAgent):
	"""
		An agent for doing a simple movement form one point to another.
	"""

	def __init__(self, model, path='logger/', model_name='model', method_name="method", method=None, load_model=False, coef_null=0, coef_neg=1, coef_pos=1, pi_lr=0.001, gamma=0.98, buffer_size=1024, clipping_range=0.2, beta=1e-3):
		super().__init__(model, path=path, model_name=model_name, method_name=method_name, method=method, load_model=load_model, coef_null=0, coef_neg=1, coef_pos=1, pi_lr=pi_lr, gamma=gamma, buffer_size=buffer_size, clipping_range=clipping_range, beta=beta)

        # Create the NET class
		self.method = method(
			model = model,
        	input_dim=[(64,64)],
        	output_dim=[64*64],
        	pi_lr=pi_lr,
        	gamma=gamma,
        	buffer_size=buffer_size,
			clipping_range = clipping_range,
			beta = beta
		)


		# Load the model
		if load_model:
            #Load the existing model
			self.epoch = self.method.load(self.path, self.method_name, self.model_name)

		self.logger.drawModel(self.method.model.model, self.path, self.method_name, self.model_name)

	def train(self, obs_new, obs, action, reward):
		# Train the agent
		self.score += reward
		if reward < 0:
			reward = reward * self.coef_neg
		elif reward == 0:
			reward = self.coef_null
		else:
			reward = reward * self.coef_pos

		feat = AgentSimple.get_feature_screen(obs, features.SCREEN_FEATURES.player_relative)
		# Store the reward
		self.method.store(feat, action, reward)
		# Increase the current step
		self.nb_steps += 1
		# Finish the episode on reward == 1
		if reward == 1 and self.nb_steps != self.max_steps and not obs_new.last():
			self.method.finish_path(reward)
		# If this is the end of the epoch or this is the last observation
		if self.nb_steps == self.max_steps or obs_new.last():
			# If this is the last observation, we bootstrap the value function
			self.method.finish_path(-1)

			# We do not train yet if this is just the end of thvvve current episode
			if obs_new.last():
				self.score_reset += 1
			if obs_new.last() is True and self.nb_steps != self.max_steps:
				return

			result = self.method.train()
			self.logger.print_train_result(self.epoch, result, self.score//self.score_reset)
			self.logger.log_train_result(self.path, self.method_name, self.model_name, self.epoch, self.score//self.score_reset, result)

			self.score_reset = 0
			self.score = 0
			self.nb_steps = 0
			self.epoch += 1
			# Save every 100 epochs
			if (self.epoch-1) % 300 == 0:
				self.method.save(self.path,self.method_name,self.model_name,self.epoch)

	def step(self, obs):
		# step function gets called automatically by pysc2 environment
		# call the parent class to have pysc2 setup rewards/etc for u
		super(AgentSimple, self).step(obs)
		# if we can move our army (we have something selected)
		# Get the features of the screen
		feat = AgentSimple.get_feature_screen(obs, features.SCREEN_FEATURES.player_relative)
		# Step with ppo according to this state
		act = self.method.get_action([feat])

		if actions.FUNCTIONS.Move_screen.id in obs.observation['available_actions']:
			# Convert the prediction into positions
			positions = AgentSimple.prediction_to_position([act])
			# Get a random location on the map
			return actions.FunctionCall(actions.FUNCTIONS.Move_screen.id, [[0], positions[0]]), act

		# if we can't move, we havent selected our army, so selecto ur army
		else:
			return actions.FunctionCall(actions.FUNCTIONS.select_army.id, [[0]]), act

	@staticmethod
	def get_feature_screen(obs, screen_feature):
		# Get the feature associated with the observation
		mapp = obs.observation["feature_screen"][screen_feature.index]
		return np.array(mapp)

	@staticmethod
	def prediction_to_position(pi, dim = 64):
		# Translate the prediction to y,x position
		pirescale = np.expand_dims(pi, axis=1)
		pirescale = np.append(pirescale, np.zeros_like(pirescale), axis=1)
		positions = np.zeros_like(pirescale)
		positions[:,0] = pirescale[:,0] // dim
		positions[:,1] = pirescale[:,0] % dim
		return positions
