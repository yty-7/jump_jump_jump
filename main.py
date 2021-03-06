# KidsCanCode - Game Development with Pygame video series
# Jumpy! (a platform game)
# Art from Kenney.nl
# Happy Tune by http://opengameart.org/users/syncopika
# Yippee by http://opengameart.org/users/snabisch

import pygame as pg
import random
from settings import *
from sprites import *
from os import path
import time
import RPi.GPIO as GPIO

class Game:
    def __init__(self):
        # initialize game window, etc
        pg.init()
        pg.mixer.init()
        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        pg.display.set_caption(TITLE)
        self.clock = pg.time.Clock()
        self.running = True
        self.font_name = pg.font.match_font(FONT_NAME)
        self.load_data()
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        def GPIO27_calllback(channel):
            self.wait = 1 
            #print("27 callback")
            
        GPIO.add_event_detect(27,GPIO.FALLING,callback=GPIO27_calllback,bouncetime=300)
              
    def load_data(self):
        # load high score
        self.dir = path.dirname(__file__)
        with open(path.join(self.dir, HS_FILE), 'r') as f:
            try:
                self.highscore = int(f.read())
            except:
                self.highscore = 0
        # load spritesheet image
        img_dir = path.join(self.dir, 'img')
        self.spritesheet = Spritesheet(path.join(img_dir, SPRITESHEET))
        # load sounds
        self.snd_dir = path.join(self.dir, 'snd')
        self.jump_sound = pg.mixer.Sound(path.join(self.snd_dir, 'Jump33.wav'))
        self.boost_sound = pg.mixer.Sound(path.join(self.snd_dir, 'Boost16.wav'))
        self.hurt_sound = pg.mixer.Sound(path.join(self.snd_dir, 'monster.wav'))
        self.background = pg.image.load(os.path.join(img_folder, "bg.png"))
        self.blood_img = pg.image.load(path.join(img_dir,'blood.png'))

    def new(self):
        # start a new game
        self.score = 0
        self.blood = 5
        self.all_sprites = pg.sprite.Group()
        self.normal_platforms = pg.sprite.Group()
        self.broken_platforms = pg.sprite.Group()
        self.pows = pg.sprite.Group()
        self.mobs = pg.sprite.Group()
        self.player = Player(self)
        self.hit_mob = 0
        self.blood = PLAYER_LIFE
        for plat in PLATFORM_LIST:
            NormalPlatform(self, *plat)
        self.mob_timer = 0
        pg.mixer.music.load(path.join(self.snd_dir, 'Happy Tune.ogg'))
        self.run()

    def run(self):
        # Game Loop
        pg.mixer.music.play(loops=-1)
        self.playing = True
        while self.playing:
            self.clock.tick(FPS)
            self.events()
            self.update()
            self.draw()
        pg.mixer.music.fadeout(500)

    def update(self):
        # Game Loop - Update
        self.all_sprites.update()

        # spawn a mob?
        now = pg.time.get_ticks()
        if now - self.mob_timer > 3500 + random.choice([-1000, -500, 0, 500, 1000]):
            self.mob_timer = now
            Mob(self)
        
        # hit mobs?
        mob_hits = pg.sprite.spritecollide(self.player, self.mobs, False, pg.sprite.collide_mask)
        if mob_hits:
            now = pg.time.get_ticks()
            if now - self.hit_mob > 500:
                self.blood -= 1
                self.hurt_sound.play()
            self.hit_mob = now
        if self.blood <= 0:
            self.playing = False

        # check if player hits a platform - only if falling
        if self.player.vel.y > 0:
            hits = pg.sprite.spritecollide(self.player, self.normal_platforms, False)
            if hits:
                lowest = hits[0]
                for hit in hits:
                    if hit.rect.bottom > lowest.rect.bottom:
                        lowest = hit
                if self.player.pos.x < lowest.rect.right + 10 and \
                   self.player.pos.x > lowest.rect.left - 10:
                    if self.player.pos.y < lowest.rect.centery:
                        self.player.pos.y = lowest.rect.top
                        self.player.vel.y = 10
                self.player.jump()
            hits = pg.sprite.spritecollide(self.player, self.broken_platforms, False)
            if hits:
                for hit in hits:
                    hit.kill()
                            

        # if player reaches top 1/4 of screen
        if self.player.rect.top <= HEIGHT / 4:
            self.player.pos.y += max(abs(self.player.vel.y), 2)
            for mob in self.mobs:
                mob.rect.y += max(abs(self.player.vel.y), 2)
            for plat in self.normal_platforms:
                plat.rect.y += max(abs(self.player.vel.y), 2)
                if plat.rect.top >= HEIGHT:
                    plat.kill()
                    self.score += 10
            for plat in self.broken_platforms:
                plat.rect.y += max(abs(self.player.vel.y), 2)
                if plat.rect.top >= HEIGHT:
                    plat.kill()
                    self.score += 10

        # if player hits life
        pow_hits = pg.sprite.spritecollide(self.player, self.pows, True)
        for pow in pow_hits:
            if pow.type == 'life':
                self.boost_sound.play()
                if self.blood < PLAYER_LIFE:
                    self.blood += 1
            if pow.type == 'boost':
                self.boost_sound.play()
                self.player.vel.y = -BOOST_POWER

        # Die!
        if self.player.rect.bottom > HEIGHT:
            for sprite in self.all_sprites:
                sprite.rect.y -= max(self.player.vel.y, 10)
                if sprite.rect.bottom < 0:
                    sprite.kill()
        if len(self.normal_platforms) == 0 and len(self.broken_platforms) == 0:
            self.playing = False

        # spawn new platforms to keep same average number
        while len(self.normal_platforms) < 5:
            width = random.randrange(50, 100)
            NormalPlatform(self, random.randrange(0, WIDTH - width), random.randrange(-75,-30))
            if random.random() < self.score / 3000:  
                BrokenPlatform(self, random.randrange(0, WIDTH - width),
                    random.randrange(-75,-30))

    def events(self):
        # Game Loop - events
        for event in pg.event.get():
            # check for closing window
            if event.type == pg.QUIT:
                if self.playing:
                    self.playing = False
                self.running = False

    def draw(self):
        # Game Loop - draw
        self.screen.blit(self.background,(0,0))
        self.all_sprites.draw(self.screen)
        self.draw_text(str(self.score), 22, TXTCOLOR, WIDTH / 2, 15)
        x_position = 15
        for _ in range(self.blood):
            self.screen.blit(self.blood_img,(x_position,15))
            x_position += 30

        # after drawing everything, flip the display
        pg.display.flip()

    def show_start_screen(self):
        # game splash/start screen
        self.wait = 0
        pg.mixer.music.load(path.join(self.snd_dir, 'Yippee.ogg'))
        pg.mixer.music.play(loops=-1)
        self.screen.blit(self.background,(0,0))
        self.draw_text(TITLE, 48, TXTCOLOR, WIDTH / 2, HEIGHT / 4)
        self.draw_text("Move the pad to move", 22, TXTCOLOR, WIDTH / 2, HEIGHT / 2)
        self.draw_text("Press the button to play", 22, TXTCOLOR, WIDTH / 2, HEIGHT * 3 / 4)
        self.draw_text("High Score: " + str(self.highscore), 22, TXTCOLOR, WIDTH / 2, 15)
        pg.display.flip()
        self.wait_for_key()
        pg.mixer.music.fadeout(500)

    def show_loading_screen(self):
        if not self.running:
            return
        pg.mixer.music.load(path.join(self.snd_dir, 'Loadingguide1.6.wav'))
        pg.mixer.music.play(loops=-1)
        picture = pg.transform.scale(pg.image.load(os.path.join(img_folder, "player.png")), (35, 35))
        step = 0
        length = 400
        while True:
            self.events()
            self.screen.blit(self.background,(0,0))
            pg.draw.rect(self.screen,WHITE,(40,500,length+10,20))
            pg.draw.rect(self.screen,PURPLE,(40,500,step % length,20))
            self.screen.blit(picture,(step % length + 40,490))

            font1 = pg.font.Font(self.font_name, 16)
            text1 = font1.render('%s %%' % str(int((step % length)/length*100)), True, (0,0,0))
            self.screen.blit(text1, (240, 500))
            step += 5
            time.sleep(0.23)
            pg.display.flip()
            if step == length:
                break

    def show_go_screen(self):
        # game over/continue
        if not self.running:
            return
        pg.mixer.music.load(path.join(self.snd_dir, 'Yippee.ogg'))
        pg.mixer.music.play(loops=-1)
        self.screen.blit(self.background,[0,0])
        if self.score < 2000:
            self.draw_text("Try it again!", 48, TXTCOLOR, WIDTH / 2, HEIGHT / 4)
        else:
            self.draw_text("You've got Potter!", 35, TXTCOLOR, WIDTH / 2, HEIGHT / 4)
            self.draw_text("Go back and save the earth!", 35, TXTCOLOR, WIDTH / 2, HEIGHT / 3)
        self.draw_text("Score: " + str(self.score), 22, TXTCOLOR, WIDTH / 2, HEIGHT / 2)
        self.draw_text("Press the button to play again", 22, TXTCOLOR, WIDTH / 2, HEIGHT * 3 / 4)
        if self.score > self.highscore:
            self.highscore = self.score
            self.draw_text("NEW HIGH SCORE!", 22, TXTCOLOR, WIDTH / 2, HEIGHT / 2 + 40)
            with open(path.join(self.dir, HS_FILE), 'w') as f:
                f.write(str(self.score))
        else:
            self.draw_text("High Score: " + str(self.highscore), 22, TXTCOLOR, WIDTH / 2, HEIGHT / 2 + 40)
        pg.display.flip()
        self.wait_for_key()
        pg.mixer.music.fadeout(500)

    def wait_for_key(self):
        waiting = True
        while waiting:
            self.clock.tick(FPS)
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    waiting = False
                    self.running = False 
                # if event.type == pg.KEYUP:
                #     waiting = False
            if  self.wait == 1:
                self.wait = 0
                waiting = False
            

    def draw_text(self, text, size, color, x, y):
        font = pg.font.Font(self.font_name, size)
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect()
        text_rect.midtop = (x, y)
        self.screen.blit(text_surface, text_rect)

g = Game()
g.show_start_screen()
g.show_loading_screen()
while g.running:
    g.new()
    g.show_go_screen()

pg.quit()
