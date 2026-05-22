# Endfield Bot

A Telegram bot built with aiogram for managing game accounts, user profiles, and character cards.

## Overview

Endfield Bot is a sophisticated Telegram bot that provides:
- User authentication and multi-account management
- Profile card generation
- Character card display with caching
- Rate limiting and request throttling
- Admin command support

## Project Structure

```
bot/
├── admin/              # Admin-only commands and operations
├── config/             # Configuration settings
├── core/               # Bot initialization, startup, and shutdown logic
├── DB/                 # Database layer
│   ├── models/         # SQLAlchemy ORM models
│   ├── repo/           # Repository pattern for data access
│   ├── asyncsessions.py # Async session management
│   ├── base.py         # Base model configuration
│   └── engine.py       # Database engine setup
├── handlers/           # Message and callback handlers
│   ├── auth/           # Authentication handlers and keyboards
│   └── cards/          # Card generation handlers
├── middleware/         # Request middlewares (DB, rate limit)
├── services/           # Business logic layer
└── utils/              # Utility functions (image processing)
```

## Database Models

### Users
- `telegram_id` (BIGINT, PK, FK)
- `username` (VARCHAR)
- `display_name` (VARCHAR)
- `banned` (BOOLEAN)
- `warns` (INTEGER)

### GameIDs
- `id` (INTEGER, PK)
- `user_id` (BIGINT, FK)
- `game_id` (INTEGER)
- `active` (BOOLEAN)
- Unique constraint: `(user_id, game_id)`

### UserSettings
- `id` (INTEGER, PK)
- `user_id` (BIGINT, FK)
- `profile_template` (INTEGER)
- `character_template` (INTEGER)

### Cache
- `id` (INTEGER, PK)
- `telegram_id` (BIGINT, FK)
- `file_id` (VARCHAR)
- `data` (VARCHAR)
- `type` (ENUM: 'PFP', 'CHAR')
- `created_at` (DATETIME)
- Unique constraint: `(telegram_id, type)`

## Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL
- Docker and Docker Compose (optional)
- Git

### Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/perlica-bot.git
cd endfield-bot
```

2. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql://user:password@localhost:5432/endfield_bot
CACHE_TTL=3600
```

5. Initialize database:
```bash
# Update main.py to run migrations if needed
python main.py
```

### Docker Setup

1. Create `.env` file with required variables

2. Start services:
```bash
docker-compose up --build
```

Services will be available at:
- Bot: Running in container
- Database: localhost:5432

## Development Guide

### Adding New Handlers

1. Create a new file in `bot/handlers/` or subdirectory
2. Import Router and decorate functions with `@rt.message()` or `@rt.callback_query()`
3. Include in `bot/handlers/routers.py`

Example:
```python
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

rt = Router()

@rt.message(Command("mycommand"))
async def handle_command(msg: Message, db_session: AsyncSession):
    await msg.reply("Hello!")
```

### Adding New Models

1. Create model class in `bot/DB/models/`
2. Inherit from `base` and use SQLAlchemy mappings
3. Create corresponding repository in `bot/DB/repo/`

### Repository Pattern

All database operations go through repositories:

```python
from bot.DB.repo.user_repo import UserRepo

user_repo = UserRepo(session)
user = await user_repo.get_user(telegram_id)
```

### Middleware

Middleware runs before handlers:
- `dbm.py`: Injects database session into handler context
- `ratelimit.py`: Applies rate limiting per user

## Commands

### User Commands

- `/login <UID>` - Authenticate with game UID
- `/logout` - Logout current account
- `/switch` - Switch between multiple accounts
- `/myuid` - Display all linked UIDs
- `/myc` - Display profile card

### Admin Commands

See `bot/admin/admin_commands.py` for admin-only operations.

## Caching System

The bot implements two-level caching:

1. **PFP Cache** - Profile card images
   - Type: 'PFP'
   - Stores generated profile cards
   - TTL: Configurable (default 3600s)

2. **CHAR Cache** - Character card images
   - Type: 'CHAR'
   - Stores character cards per slot
   - TTL: Configurable

Cache validation checks:
- Expiration time
- Slot number (for character cards)
- User ownership

## Configuration

Edit `bot/config/config.py` to modify:
- `CACHE_TTL` - Cache timeout in seconds
- Database connection settings
- Rate limit settings

## Deployment

### Manual Deployment

1. Push to private repository:
```bash
git remote add origin <private-repo-url>
git push -u origin main
```

2. Setup deployment trigger (webhook)
3. Deploy via Docker:
```bash
docker-compose pull
docker-compose up -d
```

## Error Handling

- Database errors are logged with context
- User-facing errors return friendly Telegram messages
- Admin operations validate user permissions

## Testing

Run tests (if available):
```bash
pytest tests/
```

## Troubleshooting

### Bot not responding
- Check BOT_TOKEN is valid
- Verify database connection
- Check logs: `docker-compose logs bot`

### Database errors
- Ensure PostgreSQL is running
- Verify DATABASE_URL
- Check migrations are applied

### Cache issues
- Verify CACHE_TTL setting
- Check file_id validity
- Clear cache: `await CacheRepo(session).delete_all_cache(user_id)`

## Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and test locally
3. Commit with clear messages
4. Push to private repository
5. Create pull request

## License

Proprietary - Not open source

## Support

For issues or questions, contact the development team.

## Performance Considerations

- Use connection pooling for database
- Implement cache expiration regularly
- Monitor rate limiting thresholds
- Log slow database queries
