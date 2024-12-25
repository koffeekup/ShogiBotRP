CREATE TABLE guilds (
    guild_id BIGINT PRIMARY KEY,
    guild_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE players (
    player_id SERIAL PRIMARY KEY,
    discord_user_id BIGINT NOT NULL,
    guild_id BIGINT REFERENCES guilds(guild_id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    elo INT DEFAULT 1200,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    draws INT DEFAULT 0,
    games_played INT DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (discord_user_id, guild_id)
);

CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(guild_id) ON DELETE CASCADE,
    role_name TEXT NOT NULL,
    role_type TEXT CHECK (role_type IN ('top_rank', 'elo_benchmark')) NOT NULL,
    threshold INT
);

CREATE TABLE player_roles (
    player_role_id SERIAL PRIMARY KEY,
    player_id INT REFERENCES players(player_id) ON DELETE CASCADE,
    role_id INT REFERENCES roles(role_id) ON DELETE CASCADE,
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE games (
    game_id SERIAL PRIMARY KEY,
    guild_id BIGINT REFERENCES guilds(guild_id) ON DELETE CASCADE,
    player1_id INT REFERENCES players(player_id) ON DELETE CASCADE,
    player2_id INT REFERENCES players(player_id) ON DELETE CASCADE,
    player1_color TEXT CHECK (player1_color IN ('black', 'white')) NOT NULL,
    result TEXT CHECK (result IN ('1-0', '0-1', '0.5-0.5')) NOT NULL,
    date_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
