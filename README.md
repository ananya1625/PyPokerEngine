# poker-engine

A poker game engine backend built for Chime's hack week poker bot, extending the PyPokerEngine framework with custom game management and API endpoints.

## About

This project is a semi-fork of [PyPokerEngine](https://github.com/ishikota/PyPokerEngine), a Python library for poker AI development. We've enhanced it with custom game orchestration, real-time game state management, and RESTful API endpoints to support multiplayer poker games.

## What PyPokerEngine Provides

- **Core Poker Logic**: Hand evaluation, game rules, and betting mechanics
- **Card Management**: Deck shuffling, dealing, and community card handling
- **Player Actions**: Fold, call, check, raise, and blind management
- **Game Flow**: Street progression (preflop, flop, turn, river, showdown)

## What We Built

- **Game Orchestration**: Multi-game management with unique game IDs
- **Real-time State Tracking**: Live game state updates and player turn management
- **RESTful API**: Endpoints for starting games, applying actions, and retrieving game state
- **Custom Game Logic**: Heads-up play optimization and automatic street advancement

## Use Cases

- **Multiplayer Poker Games**: Support for multiple concurrent games
- **Real-time Gaming**: Live game state updates and turn management
- **API-First Design**: Easy integration with frontend applications

## API Endpoints

### Start Game

**POST** `/start_game`

```json
{
  "game_id": "game_123",
  "players": [
    { "user_id": "player1", "stack": 1000 },
    { "user_id": "player2", "stack": 1000 }
  ]
}
```

### Apply Action

**POST** `/action`

```json
{
  "game_id": "game_123",
  "user_id": "player1",
  "action": "call",
  "amount": 0
}
```

**Actions**: `fold`, `call`, `check`, `raise`
**Note**: `amount` is required for `raise`, ignored for other actions

### Get Game State

**GET** `/state/{game_id}`
Returns current game state including pot, community cards, player positions, and next player

### End Game

**POST** `/end_game`

```json
{
  "game_id": "game_123"
}
```

## License

MIT License - same as the original PyPokerEngine project.
