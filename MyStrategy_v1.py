from math import *
from model.HockeyistState import HockeyistState
from model.Game import Game
from model.Hockeyist import Hockeyist
from model.HockeyistType import HockeyistType
from model.Move import Move
from model.Player import Player
from model.PlayerContext import PlayerContext
from model.Puck import Puck
from model.Unit import Unit
from model.World import World
from model.ActionType import ActionType

STRIKE_ANGLE = 1.0 * pi / 180.0
MAX_SPEED_UP = 1.0

HIGH_SPEED_OF_PUCK = 6.0
AVG_SPEED_OF_PUCK = 1.0
NOT_TAKE_PUCK_MODE = -1

EQUAL_HALF = 2
UP_HALF_BEST = 0
DOWN_HALF_BEST = 1
RIGHT_HALF_BEST = 0
LEFT_HALF_BEST = 1

class MyStrategy:
	high_speed = False
	avg_speed = False
	low_speed = False

	pr, p = 0, 0

	Pass = False
	tick_pass = 0

	@staticmethod
	def log(msg):
		f = open('workfile.txt', 'a')
		f.write(msg)
		f.close()

	def move(self, me, world, game, move):
		Opponent = world.get_opponent_player()
		Teammate = world.get_my_player()

		halfY = 460.0    #0.5 * (Opponent.net_bottom + Opponent.net_top)
		halfX = 600.0   #0.5 * (Opponent.net_back + Teammate.net_back)

		if self.tick_pass != 0:
			if self.tick_pass > 50:
				self.tick_pass = 0
				self.Pass = False
			else:
				self.tick_pass = self.tick_pass + 1


		# self.log("{X}:{Y}:{Z}:{W} \n".format(X=Opponent.net_bottom, Y=Opponent.net_top, Z=Opponent.net_back, W=Teammate.net_back))
		# self.log("{X}:{Y} \n".format(X=halfX, Y=halfY))

		speed_of_puck = (world.puck.speed_x ** 2 + world.puck.speed_y ** 2) ** 0.5
		# self.log("{speed}\n".format(speed=speed_of_puck))
		# self.p = world.get_my_player().goal_count
		# if self.p > self.pr:
		# 	self.pr = self.p
		# 	self.log("GOAL!\n")

		if me.state == HockeyistState.SWINGING:
			c = {}
			self.compute_point_a(c, me, world, halfX, halfY, game)

			angle_to_a = me.get_angle_to(c['x'], c['y'])
			move.turn = angle_to_a
			move.speed_up = c['speedUp']

			if (self.low_speed and me.swing_ticks == 19) or (self.avg_speed and me.swing_ticks == 10):
				move.action = ActionType.STRIKE
			if me.swing_ticks >= game.max_effective_swing_ticks: # or me.swing_ticks >= game.max_effective_swing_ticks / 2:
				move.action = ActionType.STRIKE
			return None

		if world.puck.owner_player_id == me.player_id:
			if world.puck.owner_hockeyist_id == me.id:
				# logic of attaker
				opponent = world.get_opponent_player()

				net_x = 0.5 * (opponent.net_back + opponent.net_front)
				net_y = 0.5 * (opponent.net_bottom + opponent.net_top)
				net_y += (0.5 if me.y < net_y else -0.5) * game.goal_net_height

				angle_to_net = me.get_angle_to(net_x, net_y)
				move.turn = angle_to_net

				dist_from_net_to_me = opponent.net_front - me.x
				red_line = world.width / 4.5
				line_of_attack = world.width / 3.0

				a = {}
				self.compute_point_a(a, me, world, halfX, halfY, game) # a, me, world, halfX, halfY, game
				move.speed_up = a['speedUp']
				teammate = self.get_second_teammate(me.id, me.player_id, world)


				#if (self.opponent_close(world, me, 3.5) and
				#		me.get_distance_to_unit(teammate) > world.width / 3	and
				#		abs(dist_from_net_to_me) < red_line):
				if abs(dist_from_net_to_me) < red_line:
					angle_to_teammate = me.get_angle_to_unit(self.get_second_teammate(me.id, me.player_id, world))
					move.turn = angle_to_teammate
					move.speed_up = 0
					if abs(angle_to_teammate) < STRIKE_ANGLE and teammate.state == HockeyistState.ACTIVE and self.Pass == False:
						move.action = ActionType.PASS
						self.Pass = True
						self.tick_pass = 1
				elif abs(dist_from_net_to_me) > line_of_attack: # or abs(dist_from_net_to_me) < red_line:
					angle_to_a = me.get_angle_to(a['x'], a['y'])
					move.turn = angle_to_a
				elif abs(angle_to_net) < STRIKE_ANGLE and abs(dist_from_net_to_me) <= line_of_attack:
					# if self.high_speed:
					# self.log("Speed of puck={speed}\n".format(speed=speed_of_puck))
					move.action = ActionType.SWING
					move.speed_up = a['speedUp']
					# else:
					# 	move.action = ActionType.SWING
					# 	self.log("Enter on swing, speed={speed}\n".format(speed=speed_of_puck))
					# self.back_flag = False
			else:
				# logic of defender
				if world.tick >= game.overtime_tick_count:
					opponent = self.get_nearest_opponent(world.puck.x, world.puck.y, world)

					if (me.get_angle_to_unit(opponent) <= game.stick_length and
							me.get_angle_to_unit(opponent) < 0.5 * game.stick_sector):
						move.action = ActionType.STRIKE

					move.turn = me.get_angle_to_unit(world.puck)
					move.speed_up = MAX_SPEED_UP
				else:
					self.run_defensive_strategy(me, world, game, move, NOT_TAKE_PUCK_MODE)
		else:
			if world.tick >= game.overtime_tick_count:
				if world.puck.owner_player_id == world.get_opponent_player().id:
					opponent_with_puck = self.get_hockeyist_by_id(world.hockeyists, world.puck.owner_hockeyist_id)

					opponentPlayer = world.get_opponent_player()
					dist_from_net_to_me = opponentPlayer.net_front - me.x
					net_on_the_left = True if dist_from_net_to_me < 0 else False

					if (me.get_distance_to_unit(world.puck) <= game.stick_length and
							me.get_angle_to_unit(world.puck) < 0.5 * game.stick_sector):
						if net_on_the_left:
							move.action = ActionType.STRIKE if world.puck.x > halfX else ActionType.TAKE_PUCK
						else:
							move.action = ActionType.TAKE_PUCK if world.puck.x > halfX else ActionType.STRIKE
					elif (me.get_angle_to_unit(opponent_with_puck) <= game.stick_length and
							me.get_angle_to_unit(opponent_with_puck) < 0.5 * game.stick_sector):
						move.action = ActionType.STRIKE
				else:
					move.action = ActionType.TAKE_PUCK

				move.turn = me.get_angle_to_unit(world.puck)
				move.speed_up = MAX_SPEED_UP
			else:
				my_player = world.get_my_player()

				center_net_x = 0.5 * (my_player.net_back + my_player.net_front)
				center_net_y = 0.5 * (my_player.net_bottom + my_player.net_top)

				nearest_teammate = self.get_nearest_teammate(center_net_x, center_net_y, world)

				if me.id != nearest_teammate.id:
					# logic of attacker
					if world.puck.owner_player_id == world.get_opponent_player().id:
						opponent_with_puck = self.get_hockeyist_by_id(world.hockeyists, world.puck.owner_hockeyist_id)
						opponentPlayer = world.get_opponent_player()
						dist_from_net_to_me = opponentPlayer.net_front - me.x
						net_on_the_left = True if dist_from_net_to_me < 0 else False

						if (me.get_distance_to_unit(world.puck) <= game.stick_length and
								me.get_angle_to_unit(world.puck) < 0.5 * game.stick_sector):
							if net_on_the_left:
								move.action = ActionType.STRIKE if world.puck.x > halfX else ActionType.TAKE_PUCK
							else:
								move.action = ActionType.TAKE_PUCK if world.puck.x > halfX else ActionType.STRIKE
						elif (me.get_angle_to_unit(opponent_with_puck) <= game.stick_length and
								me.get_angle_to_unit(opponent_with_puck) < 0.5 * game.stick_sector):
							move.action = ActionType.STRIKE
					else:
						move.action = ActionType.TAKE_PUCK

					move.turn = me.get_angle_to_unit(world.puck)
					move.speed_up = MAX_SPEED_UP
				else:
					# logic of defender
					self.run_defensive_strategy(me, world, game, move, 5)

	def opponent_close(self, world, me, coef):
		danger = True
		for hockeyist in world.hockeyists:
			if (hockeyist.teammate or hockeyist.type == HockeyistType.GOALIE or
					hockeyist.state == HockeyistState.RESTING):
				continue

			if me.get_distance_to_unit(hockeyist) >  coef * hockeyist.radius:
				danger = False

		return danger

	def compute_point_a(self, a, me, world, halfX, halfY, game):
		bestHalfGorizont = self.get_best_half_gorizont(world.hockeyists, world, me, halfX, halfY) # hockeyists, world, me, halfX, halfY
		opponent = world.get_opponent_player()

		net_x = 0.5 * (opponent.net_back + opponent.net_front)
		dist_from_net_to_me = opponent.net_front - me.x
		net_on_the_left = True if dist_from_net_to_me < 0 else False

		net_x = 0.5 * (opponent.net_back + opponent.net_front)
		net_y = 0.5 * (opponent.net_bottom + opponent.net_top)
		net_y += (0.5 if me.y < net_y else -0.5) * game.goal_net_height

		if net_on_the_left and me.x <= halfX or net_on_the_left == False and me.x >= halfX:
			a['speedUp'] = MAX_SPEED_UP / 3

		if net_on_the_left and me.x > halfX or net_on_the_left == False and me.x < halfX:
			a['x'] = halfX
			a['y'] = halfY + world.height * (-1 if bestHalfGorizont == UP_HALF_BEST else 1) / 2 + 5.5 * me.radius *(1 if bestHalfGorizont == UP_HALF_BEST else -1)
			a['speedUp'] = MAX_SPEED_UP
		# elif net_on_the_left and me.x > halfX - world.width / 10 or net_on_the_left == False and me.x < halfX + world.width / 10:
		# 	a['x'] = halfX - world.width / 10 if net_on_the_left else halfX + world.width / 10
		# 	a['y'] = halfY + world.height * (-1 if me.y < halfY else 1) / 2 + 6 * me.radius *(1 if me.y < halfY else -1)
		# 	a['speedUp'] = MAX_SPEED_UP / 2
		else:
			a['x'] = net_x
			a['y'] = net_y
			a['speedUp'] = MAX_SPEED_UP / 3

		# coef_of_width = 3.0
		# coef_of_height = 10.0
		# coef_of_area = 1.5
		#
		# a['x'] = world.width / coef_of_width if net_on_the_left else net_x - world.width / coef_of_width
		# if me.y > world.height / 2:
		# 	if bestHalfGorizont == UP_HALF_BEST and abs(net_x - me.x) >= world.width / coef_of_area:
		# 		a['y'] = opponent.net_top - world.height / coef_of_height
		# 	else:
		# 		a['y'] = opponent.net_bottom + world.height / coef_of_height
		# else:
		# 	if bestHalfGorizont == DOWN_HALF_BEST and abs(net_x - me.x) >= world.width / coef_of_area:
		# 		a['y'] = opponent.net_bottom + world.height / coef_of_height
		# 	else:
		# 		a['y'] = opponent.net_top - world.height / coef_of_height

		return None

	def get_best_half_gorizont(self, hockeyists, world, me, halfX, halfY):
		opponent = world.get_opponent_player()
		net_x = 0.5 * (opponent.net_back + opponent.net_front)
		dist_from_net_to_me = opponent.net_front - me.x
		net_on_the_left = True if dist_from_net_to_me < 0 else False

		count_up_and_knock, count_down_and_knock = 0, 0
		count_up, count_down = 0, 0

		for hockeyist in hockeyists:
			if (hockeyist.teammate or hockeyist.type == HockeyistType.GOALIE or
					hockeyist.state == HockeyistState.RESTING):
				continue

			if net_on_the_left:
				if hockeyist.x > halfX:
					continue
			else:
				if hockeyist.x < halfX:
					continue

			if hockeyist.y > halfY:
				if hockeyist.state == HockeyistState.KNOCKED_DOWN:
					count_down_and_knock += 1
				else:
					count_down += 1
			else:
				if hockeyist.state == HockeyistState.KNOCKED_DOWN:
					count_up_and_knock += 1
				else:
					count_up += 1

		if count_down == count_up:
			return UP_HALF_BEST if me.y < halfY else DOWN_HALF_BEST
		elif count_down > count_up:
			return UP_HALF_BEST
		elif count_down < count_up:
			return DOWN_HALF_BEST
		elif count_down_and_knock > count_up_and_knock:
			return UP_HALF_BEST
		elif count_down_and_knock < count_up_and_knock:
			return DOWN_HALF_BEST
		else:
			return UP_HALF_BEST if me.y < halfY else DOWN_HALF_BEST

	def get_best_half_vertical(self, hockeyists, world_width):
		# check hor
		count_right, count_left = 0, 0

		for hockeyist in hockeyists:
			if (hockeyist.teammate or hockeyist.type == HockeyistType.GOALIE or
					hockeyist.state == HockeyistState.RESTING):
				continue
			if hockeyist.y > world_width / 2:
				count_right += 1
			else:
				count_left += 1

		if count_right == count_left:
			return EQUAL_HALF
		elif count_right > count_left:
			return LEFT_HALF_BEST
		else:
			return RIGHT_HALF_BEST

	def get_hockeyist_by_id(self, hockeyists, id):
		for hockeyist in hockeyists:
			if hockeyist.id == id:
				return hockeyist

	def update_state_opponent(self, world, count):
		enemy = []
		for hockeyist in world.hockeyists:
			if (hockeyist.teammate or hockeyist.type == HockeyistType.GOALIE or
					hockeyist.state == HockeyistState.RESTING):
				continue

			if hockeyist.angle == world.puck.angle:
				enemy.append(hockeyist)

		if len(enemy) != count:
			self.both_enemy_catch = False
			return None

		if count == 2:
			if Unit.get_distance_to_unit(enemy[0], enemy[1]) < world.width / 8:
				self.both_enemy_catch = True

	def get_second_teammate(self, attacked_id, player_id, world):
		if world.puck.owner_player_id != player_id:
			return None
		for hockeyist in world.hockeyists:
			if hockeyist.teammate and hockeyist.id != attacked_id:
				return hockeyist

	def get_second_teammate_2(self, attacked_id, player_id, world):
		for hockeyist in world.hockeyists:
			if hockeyist.teammate and hockeyist.id != attacked_id:
				return hockeyist

	def get_nearest_opponent(self, x, y, world):
		nearest_opponent = None
		nearest_opponent_range = 0.0

		for hockeyist in world.hockeyists:
			if (hockeyist.teammate or hockeyist.type == HockeyistType.GOALIE or
					hockeyist.state == HockeyistState.KNOCKED_DOWN or
					hockeyist.state == HockeyistState.RESTING):
				continue

			opponent_range = hypot(x - hockeyist.x, y - hockeyist.y)

			if nearest_opponent == None or opponent_range < nearest_opponent_range:
				nearest_opponent = hockeyist
				nearest_opponent_range = opponent_range

		return nearest_opponent

	def get_nearest_teammate(self, x, y, world):
		nearest_teammate = None
		nearest_teammate_range = 0.0

		for hockeyist in world.hockeyists:
			if (hockeyist.teammate == False or hockeyist.type == HockeyistType.GOALIE or
					hockeyist.state == HockeyistState.KNOCKED_DOWN or hockeyist.state == HockeyistState.RESTING):
				continue

			teammate_range = hypot(x - hockeyist.x, y - hockeyist.y)

			if nearest_teammate == None or teammate_range < nearest_teammate_range:
				nearest_teammate = hockeyist
				nearest_teammate_range = teammate_range

		return nearest_teammate

	def run_defensive_strategy(self, me, world, game, move, coef_of_activity_puck):
		player_with_puck = world.puck.owner_hockeyist_id
		opponent_with_puck = None
		my_player = world.get_my_player()
		opponent_player = world.get_opponent_player()
		center_net_x = 0.5 * (my_player.net_back + my_player.net_front)
		center_net_y = 0.5 * (my_player.net_bottom + my_player.net_top)
		nearest_opponent = self.get_nearest_opponent(center_net_x, center_net_y, world)
		net_x = center_net_x
		net_y = center_net_y
		coef_of_activity = me.radius / 2 # 10  # was 9
		coef_of_radius = 4.0
		part_of_activity = me.radius # world.width / coef_of_activity
		dist_from_center_net_to_me = me.get_distance_to(center_net_x, center_net_y)

		dist_from_net_to_me = opponent_player.net_front - me.x
		left = True if dist_from_net_to_me < 0 else False

		for hockeyist in world.hockeyists:
			if (hockeyist.teammate or hockeyist.type == HockeyistType.GOALIE or
					hockeyist.state == HockeyistState.KNOCKED_DOWN or
					hockeyist.state == HockeyistState.RESTING):
				continue

			if player_with_puck == hockeyist.id:
				opponent_with_puck = hockeyist
				break

		if opponent_with_puck != None:
			net_y += (0.5 if opponent_with_puck.y < net_y else -0.5) * game.goal_net_height
		else:
			net_y += (0.5 if nearest_opponent.y < net_y else -0.5) * game.goal_net_height

		angle_to_net = me.get_angle_to(center_net_x + coef_of_radius * me.radius * (-1 if left else 1),
		    center_net_y)
		angle_to_puck = me.get_angle_to_unit(world.puck)
		dist_from_me_to_b = me.get_distance_to(center_net_x + coef_of_radius * me.radius * (-1 if left else 1),
		    center_net_y)
		move.speed_up = (MAX_SPEED_UP if dist_from_me_to_b > part_of_activity * 6
		                 else 0.2 if dist_from_me_to_b > part_of_activity else 0.0)

		move.turn = angle_to_net if dist_from_me_to_b > part_of_activity else angle_to_puck

		dist_from_me_to_puck = me.get_distance_to_unit(world.puck)
		part_of_activity_puck = game.stick_length # world.width / coef_of_activity_puck

		teammate = self.get_second_teammate_2(me.id, me.player_id, world)

		if teammate.last_action == ActionType.PASS and me.state == HockeyistState.ACTIVE or self.Pass:
			move.speed_up = MAX_SPEED_UP / 2
			move.turn = me.get_angle_to_unit(world.puck)
			move.action = ActionType.TAKE_PUCK
		elif dist_from_me_to_puck <= part_of_activity_puck and coef_of_activity_puck != NOT_TAKE_PUCK_MODE:
			move.speed_up = MAX_SPEED_UP
			move.turn = me.get_angle_to_unit(world.puck)
			move.action = ActionType.STRIKE

		return None
