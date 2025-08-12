#!/usr/bin/env python3
"""Script to create test data for the Gomoku application."""

import sys
import asyncio
import httpx
from loguru import logger


async def setup_test_data():
    """Create test users and a ruleset for testing."""
    
    async with httpx.AsyncClient(base_url="http://localhost:8001") as client:
        try:
            # Check if server is running
            response = await client.get("/")
            logger.info(f"Server status: {response.status_code}")
            
            # Create test users
            users = []
            for i in range(1, 3):
                user_data = {
                    "username": f"player{i}",
                    "email": f"player{i}@example.com",
                    "display_name": f"Player {i}"
                }
                
                try:
                    response = await client.post("/api/v1/users/", json=user_data)
                    if response.status_code == 201:
                        user = response.json()
                        users.append(user)
                        logger.info(f"Created user: {user['display_name']} (ID: {user['id']})")
                    elif response.status_code == 400:
                        # User might already exist
                        logger.info(f"User {user_data['username']} might already exist")
                        # Try to get the user
                        response = await client.get("/api/v1/users/")
                        all_users = response.json()
                        for u in all_users:
                            if u['username'] == user_data['username']:
                                users.append(u)
                                logger.info(f"Found existing user: {u['display_name']} (ID: {u['id']})")
                                break
                except Exception as e:
                    logger.error(f"Error creating/finding user {i}: {e}")
            
            # Create a test ruleset
            ruleset_data = {
                "name": "Standard Gomoku",
                "board_size": 15,
                "allow_overlines": True,
                "rules": {
                    "description": "Standard Gomoku rules - 5 in a row wins",
                    "opening_rule": "none"
                }
            }
            
            try:
                response = await client.post("/api/v1/rulesets/", json=ruleset_data)
                if response.status_code == 201:
                    ruleset = response.json()
                    logger.info(f"Created ruleset: {ruleset['name']} (ID: {ruleset['id']})")
                elif response.status_code == 400:
                    # Ruleset might already exist
                    logger.info("Ruleset might already exist")
                    response = await client.get("/api/v1/rulesets/")
                    all_rulesets = response.json()
                    if all_rulesets:
                        logger.info(f"Found {len(all_rulesets)} existing rulesets")
            except Exception as e:
                logger.error(f"Error creating ruleset: {e}")
            
            # Create a test game
            if len(users) >= 2:
                game_data = {
                    "black_player_id": users[0]["id"],
                    "white_player_id": users[1]["id"],
                    "ruleset_id": 1  # Assume first ruleset
                }
                
                try:
                    response = await client.post("/api/v1/games/", json=game_data)
                    if response.status_code == 201:
                        game = response.json()
                        logger.info(f"Created test game: {game['id']}")
                        logger.info(f"  Black: {users[0]['display_name']}")
                        logger.info(f"  White: {users[1]['display_name']}")
                        logger.info(f"  Status: {game['status']}")
                except Exception as e:
                    logger.error(f"Error creating game: {e}")
            
            logger.info("Test data setup complete!")
            
        except httpx.ConnectError:
            logger.error("Could not connect to backend server. Is it running?")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")
    
    import sys
    asyncio.run(setup_test_data())