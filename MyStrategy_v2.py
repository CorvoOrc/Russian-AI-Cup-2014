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

PASS_TICK_FINISH = 1000

LOW_SPEED_LIMIT = 4.0

COEF_RED_LINE = 10.0
COEF_ATTACK_LINE = 2.8

class Attaker:
	def __init__(self, id, x, y):
		self.id = id
		self.x = x
		self.y = y
		self.turn = 0
		self.speedUp = 0.0
		self.action = ActionType.NONE
		self.is_puck_owner = False
		self.pass_wait = False
		self.pass_timer = 0

class Defender:
	def __init__(self, id, x, y):
		self.id = id
		self.x = x
		self.y = y
		self.turn = 0
		self.speedUp = 0.0
		self.action = ActionType.NONE
		self.is_puck_owner = False
		self.pass_wait = False
		self.pass_timer = 0

class MyStrategy:
	high_speed = False
	avg_speed = False
	low_speed = False

	pr, p = 0, 0

	Pass = False
	tick_pass = 0

	halfY, halfX = 460.0, 600.0

	defender = attacker = None

	who_pass_id = 0
	whom_pass_id = 0

	count_teammate = 0

	red_line = 0
	attack_line = 0

	is_init = False

	danger = False
	doPass = False

	wait = False

	def init(self, world, me):
		my_player = world.get_my_player()

		center_net_x = 0.5 * (my_player.net_back + my_player.net_front)
		center_net_y = 0.5 * (my_player.net_bottom + my_player.net_top)

		defender = self.get_nearest_teammate(center_net_x, center_net_y, world)
		attacker = self.get_second_teammate_2(defender.id, my_player.id, world)

		self.compute_count_teammate(world.hockeyists)

		self.defender = Defender(defender.id, defender.x, defender.y)
		self.attacker = Attaker(attacker.id, attacker.x, attacker.y)

		opponent = world.get_opponent_player()

		self.halfX = 0.5 * (opponent.net_back + my_player.net_back)
		self.halfY = 0.5 * (opponent.net_bottom + opponent.net_top)

		self.red_line = world.width / COEF_RED_LINE
		self.attack_line = world.width / COEF_ATTACK_LINE

		self.who_pass_id = me.id
		self.whom_pass_id = self.get_second_teammate_2(self.who_pass_id, me.player_id, world)

		self.is_init = True

	@staticmethod
	def log(msg):
		f = open('workfile.txt', 'a')
		f.write(msg)
		f.close()

	def compute_count_teammate(self, hockeyists):
		for hockeyist in hockeyists:
			if hockeyist.teammate and hockeyist.type != HockeyistType.GOALIE:
				self.count_teammate += 1

	def move(self, me, world, game, move):
		# print "{P}\n".format(P=self.Pass)
		if self.is_init == False:
			self.init(world, me)

		opponent = world.get_opponent_player()
		speed_of_puck = (world.puck.speed_x ** 2 + world.puck.speed_y ** 2) ** 0.5
		dist_from_net_to_me = opponent.net_front - me.x
		net_on_the_left = True if dist_from_net_to_me < 0 else False

		whom_pass = self.get_hockeyist_by_id(world.hockeyists, self.whom_pass_id)
		print whom_pass
		if self.Pass and whom_pass != None and (net_on_the_left and world.puck.x > whom_pass.x or
				net_on_the_left == False and world.puck.x < whom_pass.x):
			self.Pass = False
			self.tick_pass = 0

		if speed_of_puck < LOW_SPEED_LIMIT:
			self.low_speed = True
			self.high_speed = False
		else:
			self.low_speed = False
			self.high_speed = True

		if me.state == HockeyistState.SWINGING:
			coef_of_swing = 1

			if world.tick >= world.tick_count:
				coef_of_swing = game.max_effective_swing_ticks / 2

			if me.swing_ticks >= game.max_effective_swing_ticks / coef_of_swing:
				move.action = ActionType.STRIKE
			return None

		if world.puck.owner_player_id == me.player_id:
			if world.puck.owner_hockeyist_id == me.id:
				# logic of attaker
				teammate = self.get_second_teammate(me.id, me.player_id, world)

				if self.doPass:
					angle_to_teammate = me.get_angle_to_unit(teammate)
					move.turn = angle_to_teammate
					move.speed_up = 0.0

					if teammate.state == HockeyistState.ACTIVE and abs(angle_to_teammate) < 10 * STRIKE_ANGLE:
						move.action = ActionType.PASS
						move.pass_power = 0.7
						move.pass_angle = me.get_angle_to_unit(teammate)
						self.tick_pass = 0
						self.Pass = True
						self.doPass = False

					return None

				self.Pass = False
				self.tick_pass = 0

				net_x = 0.5 * (opponent.net_back + opponent.net_front)
				net_y = 0.5 * (opponent.net_bottom + opponent.net_top)
				net_y += (0.5 if me.y < net_y else -0.5) * game.goal_net_height

				a = {}
				self.compute_point(a, me, world, game)
				move.speed_up = a['speedUp']

				if abs(dist_from_net_to_me) < self.red_line:
					angle_to_teammate = me.get_angle_to_unit(teammate)
					move.turn = angle_to_teammate
					move.speed_up = 0.0

					if teammate.state == HockeyistState.ACTIVE and abs(angle_to_teammate) < 10 * STRIKE_ANGLE:
						move.action = ActionType.PASS
						move.pass_power = 0.7
						move.pass_angle = me.get_angle_to_unit(teammate)
						self.tick_pass = 0
						self.Pass = True
						self.assign_responsibilities(me.id, self.get_second_teammate_2(me.id, me.player_id, world).id)
				elif abs(dist_from_net_to_me) > self.attack_line:
					if (self.danger_zone_for_attacker(me, world, net_on_the_left) and
						    me.get_distance_to_unit(self.get_second_teammate_2(me.id, me.player_id, world)) >= self.attack_line):
						angle_to_teammate = me.get_angle_to_unit(teammate)
						move.turn = angle_to_teammate
						move.speed_up = 0.0
						self.doPass = True

						if teammate.state == HockeyistState.ACTIVE and abs(angle_to_teammate) < 10 * STRIKE_ANGLE:
							move.action = ActionType.PASS
							move.pass_power = 0.7
							move.pass_angle = me.get_angle_to_unit(teammate)
							self.tick_pass = 0
							self.Pass = True
							self.doPass = False
							self.assign_responsibilities(me.id, self.get_second_teammate_2(me.id, me.player_id, world).id)
					else:
						move.turn = me.get_angle_to(a['x'], a['y'])
				elif abs(me.get_angle_to(net_x, net_y)) < STRIKE_ANGLE and abs(dist_from_net_to_me) <= self.attack_line:
					if self.danger_zone(me, world):
						move.action = ActionType.PASS
						move.pass_power = 1.0
						move.pass_angle = me.get_angle_to(net_x, net_y)
					else:
						move.action = ActionType.SWING
			else:
				self.run_defensive_strategy(me, world, game, move, NOT_TAKE_PUCK_MODE)
		else: # puck is free or from opponent
			# compute who from teammate nearest to net
			my_player = world.get_my_player()

			center_net_x = 0.5 * (my_player.net_back + my_player.net_front)
			center_net_y = 0.5 * (my_player.net_bottom + my_player.net_top)

			nearest_teammate = self.get_nearest_teammate(center_net_x, center_net_y, world)

			# nearest - defender, second - attacker
			if me.id != nearest_teammate.id:
				# logic of attacker
				if world.puck.owner_player_id == world.get_opponent_player().id:
					opponent_with_puck = self.get_hockeyist_by_id(world.hockeyists, world.puck.owner_hockeyist_id)
					# opponent_player = world.get_opponent_player()
					dist_from_net_to_me = opponent.net_front - me.x
					net_on_the_left = True if dist_from_net_to_me < 0 else False

					if (me.get_distance_to_unit(world.puck) <= game.stick_length and
							me.get_angle_to_unit(world.puck) < 0.5 * game.stick_sector):
						if net_on_the_left:
							if world.puck.x > self.halfX:
								move.action = ActionType.STRIKE
							else:
								net_x = 0.5 * (opponent.net_back + opponent.net_front)
								net_y = 0.5 * (opponent.net_bottom + opponent.net_top)
								net_y += (0.5 if me.y < net_y else -0.5) * game.goal_net_height

								if me.get_angle_to(net_x, net_y) < STRIKE_ANGLE:
									move.action = ActionType.STRIKE
								else:
									move.action = ActionType.TAKE_PUCK
						else:
							if world.puck.x < self.halfX and self.danger_zone_for_attacker(me, world, net_on_the_left):
								move.action = ActionType.STRIKE
							else:
								net_x = 0.5 * (opponent.net_back + opponent.net_front)
								net_y = 0.5 * (opponent.net_bottom + opponent.net_top)
								net_y += (0.5 if me.y < net_y else -0.5) * game.goal_net_height

								if me.get_angle_to(net_x, net_y) < STRIKE_ANGLE:
									move.action = ActionType.STRIKE
								else:
									move.action = ActionType.TAKE_PUCK
					elif (me.get_angle_to_unit(opponent_with_puck) <= game.stick_length and
							me.get_angle_to_unit(opponent_with_puck) < 0.5 * game.stick_sector):
						move.action = ActionType.STRIKE
				else:
					if (me.get_distance_to_unit(world.puck) <= game.stick_length and
							me.get_angle_to_unit(world.puck) < 0.5 * game.stick_sector and self.high_speed):
						move.action = ActionType.STRIKE
					else:
						move.action = ActionType.TAKE_PUCK

				move.turn = me.get_angle_to_unit(world.puck)
				move.speed_up = MAX_SPEED_UP
			else:
				# logic of defender
				self.run_defensive_strategy(me, world, game, move, 5)
				print self.Pass

				if self.Pass:
					move.turn = me.get_angle_to_unit(world.puck)
					move.speed_up = 0.0
					move.action = ActionType.TAKE_PUCK

					if self.tick_pass == PASS_TICK_FINISH:
						self.Pass = False
						self.tick_pass = 0
					else:
						self.tick_pass += 1

	def assign_responsibilities(self, who, whom):
		self.who_pass_id = who
		self.whom_pass_id = whom


	def danger_zone_for_attacker(self, me, world, left):
		counter = 0
		for o in world.hockeyists:
			if (o.teammate or o.type == HockeyistType.GOALIE or
					o.state == HockeyistState.RESTING):
				continue

			if (left and o.x < me.x and o.x > me.x - world.width / 12 and
					o.y < me.y + world.height / 7 and o.y > me.y - world.height / 7):
				counter += 1
			elif(left == False and o.x < me.x + world.width / 12 and o.x > me.x and
					o.y < me.y + world.height / 7 and o.y > me.y - world.height / 7):
				counter += 1

		return False if counter < 2 else True

	def danger_zone(self, me, world):
		for o in world.hockeyists:
			if (o.teammate or o.type == HockeyistType.GOALIE or
					o.state == HockeyistState.RESTING):
				continue

			if (o.x < me.x + world.width / 9 and o.x > me.x - world.width / 9 and
					o.y < me.y + world.height / 5 and o.y > me.y - world.height / 5):
				return True

		return False

	def opponent_close(self, world, me, coef):
		danger = True
		for hockeyist in world.hockeyists:
			if (hockeyist.teammate or hockeyist.type == HockeyistType.GOALIE or
					hockeyist.state == HockeyistState.RESTING):
				continue

			if me.get_distance_to_unit(hockeyist) >  coef * hockeyist.radius:
				danger = False

		return danger

	def compute_point(self, a, me, world, game):
		best_half_gorizont = self.get_best_half_gorizont(world.hockeyists, world, me)
		opponent = world.get_opponent_player()

		dist_from_net_to_me = opponent.net_front - me.x
		net_on_the_left = True if dist_from_net_to_me < 0 else False

		net_x = 0.5 * (opponent.net_back + opponent.net_front)
		net_y = 0.5 * (opponent.net_bottom + opponent.net_top)
		net_y += (0.5 if me.y < net_y else -0.5) * game.goal_net_height

		if net_on_the_left and me.x <= self.halfX or net_on_the_left == False and me.x >= self.halfX:
			a['speedUp'] = MAX_SPEED_UP / 3

		if net_on_the_left and me.x > self.halfX or net_on_the_left == False and me.x < self.halfX:
			a['x'] = self.halfX
			a['y'] = (self.halfY + world.height * (-1 if best_half_gorizont == UP_HALF_BEST else 1) / 2 +
						5.5 * me.radius *(1 if best_half_gorizont == UP_HALF_BEST else -1))
			a['speedUp'] = MAX_SPEED_UP
		else:
			a['x'] = net_x
			a['y'] = net_y
			a['speedUp'] = MAX_SPEED_UP / 3

		return None

	def get_best_half_gorizont(self, hockeyists, world, me):
		opponent = world.get_opponent_player()
		dist_from_net_to_me = opponent.net_front - me.x
		net_on_the_left = True if dist_from_net_to_me < 0 else False

		count_up_and_knock, count_down_and_knock = 0, 0
		count_up, count_down = 0, 0

		for hockeyist in hockeyists:
			if (hockeyist.teammate or hockeyist.type == HockeyistType.GOALIE or
					hockeyist.state == HockeyistState.RESTING):
				continue

			if net_on_the_left:
				if hockeyist.x > self.halfX:
					continue
			else:
				if hockeyist.x < self.halfX:
					continue

			if hockeyist.y > self.halfY:
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
			return UP_HALF_BEST if me.y < self.halfY else DOWN_HALF_BEST
		elif count_down > count_up:
			return UP_HALF_BEST
		elif count_down < count_up:
			return DOWN_HALF_BEST
		elif count_down_and_knock > count_up_and_knock:
			return UP_HALF_BEST
		elif count_down_and_knock < count_up_and_knock:
			return DOWN_HALF_BEST
		else:
			return UP_HALF_BEST if me.y < self.halfY else DOWN_HALF_BEST

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
			if hockeyist.teammate and hockeyist.id != attacked_id and hockeyist.type != HockeyistType.GOALIE:
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
			if (hockeyist.teammate == False or hockeyist.type == HockeyistType.GOALIE
				or hockeyist.state == HockeyistState.RESTING):
				continue

			teammate_range = hypot(x - hockeyist.x, y - hockeyist.y)

			if nearest_teammate == None or teammate_range < nearest_teammate_range:
				nearest_teammate = hockeyist
				nearest_teammate_range = teammate_range

		return nearest_teammate

	def run_defensive_strategy(self, me, world, game, move, coef_of_activity_puck):
		speed_of_puck = (world.puck.speed_x ** 2 + world.puck.speed_y ** 2) ** 0.5

		if self.Pass: return None

		player_with_puck = world.puck.owner_hockeyist_id
		opponent_with_puck = None
		my_player = world.get_my_player()
		opponent_player = world.get_opponent_player()
		center_net_x = 0.5 * (my_player.net_back + my_player.net_front)
		center_net_y = 0.5 * (my_player.net_bottom + my_player.net_top)
		nearest_opponent = self.get_nearest_opponent(center_net_x, center_net_y, world)
		net_x = center_net_x
		net_y = center_net_y
		coef_of_activity = me.radius / 2
		coef_of_radius = 6.0
		part_of_activity = me.radius * 3 # world.width / coef_of_activity
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

		angle_to_net = me.get_angle_to(center_net_x + coef_of_radius * me.radius * (-1 if left else 1),
		    center_net_y)
		angle_to_puck = me.get_angle_to_unit(world.puck)
		dist_from_me_to_b = me.get_distance_to(center_net_x + coef_of_radius * me.radius * (-1 if left else 1),
		    center_net_y)
		move.speed_up = (MAX_SPEED_UP if dist_from_me_to_b > part_of_activity * 6
		                 else 1.0 if dist_from_me_to_b > part_of_activity else 0.0)

		move.turn = angle_to_net if dist_from_me_to_b > part_of_activity else angle_to_puck

		if left and world.puck.x >= self.halfX or left == False and world.puck.x <= self.halfX:
			if coef_of_activity_puck != NOT_TAKE_PUCK_MODE:
				if world.puck.owner_player_id == -1:
					move.action = ActionType.TAKE_PUCK

					if world.puck.x < self.halfX and self.danger_zone_for_attacker(me, world, left):
						move.action = ActionType.STRIKE

					move.turn = me.get_angle_to_unit(world.puck)
				elif(me.get_distance_to_unit(world.puck) <= game.stick_length and
						me.get_angle_to_unit(world.puck) < 0.5 * game.stick_sector):
					move.action = ActionType.STRIKE
					move.turn = me.get_angle_to_unit(world.puck)
				elif (me.get_distance_to_unit(nearest_opponent) <= game.stick_length and
						me.get_angle_to_unit(nearest_opponent) < 0.5 * game.stick_sector):
					move.action = ActionType.STRIKE
					move.turn = me.get_angle_to_unit(nearest_opponent)
				else:
					move.turn = me.get_angle_to_unit(world.puck)
				move.speed_up = MAX_SPEED_UP
			else:

				if world.puck.owner_player_id == -1:
					move.action = ActionType.TAKE_PUCK
					move.turn = me.get_angle_to_unit(world.puck)
				elif left and nearest_opponent.x > self.halfX or left == False and nearest_opponent.x > self.halfX:
					if (me.get_angle_to_unit(nearest_opponent) <= game.stick_length and
							me.get_angle_to_unit(nearest_opponent) < 0.5 * game.stick_sector):
						move.action = ActionType.STRIKE
						move.turn = me.get_angle_to_unit(nearest_opponent)
				move.speed_up = MAX_SPEED_UP
		elif (left and world.puck.x >= self.halfX - self.halfX / 5 or left == False and world.puck.x <= self.halfX + self.halfX / 5 and
				coef_of_activity_puck != NOT_TAKE_PUCK_MODE):
			move.speed_up = MAX_SPEED_UP - 0.5
			move.turn = me.get_angle_to(self.halfX + me.radius * (1 if left else -1), world.puck.y)
			move.action = ActionType.TAKE_PUCK


		# if teammate.last_action == ActionType.PASS and me.state == HockeyistState.ACTIVE or self.Pass:
		# 	move.speed_up = MAX_SPEED_UP / 2
		# 	move.turn = me.get_angle_to_unit(world.puck)
		# 	move.action = ActionType.TAKE_PUCK
		# elif dist_from_me_to_puck <= part_of_activity_puck and coef_of_activity_puck != NOT_TAKE_PUCK_MODE:
		# 	move.speed_up = MAX_SPEED_UP
		# 	move.turn = me.get_angle_to_unit(world.puck)
		# 	move.action = ActionType.STRIKE

		return None
