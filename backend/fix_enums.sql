-- Fix enum values to be lowercase in the database
-- This script updates the check constraints to accept lowercase enum values

-- Drop and recreate the check constraint for GameStatus
ALTER TABLE games DROP CONSTRAINT IF EXISTS games_status_check;
ALTER TABLE games ADD CONSTRAINT games_status_check CHECK (status IN ('waiting', 'active', 'finished', 'abandoned'));

-- Drop and recreate the check constraint for Player
ALTER TABLE games DROP CONSTRAINT IF EXISTS games_current_player_check;
ALTER TABLE games ADD CONSTRAINT games_current_player_check CHECK (current_player IN ('black', 'white'));

ALTER TABLE game_moves DROP CONSTRAINT IF EXISTS game_moves_player_color_check;
ALTER TABLE game_moves ADD CONSTRAINT game_moves_player_color_check CHECK (player_color IN ('black', 'white'));