# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base  # noqa
from app.models.user import User  # noqa
from app.models.refresh_token import RefreshToken  # noqa
from app.models.hotel import Hotel, Room  # noqa
from app.models.booking import Booking, PriceAlert  # noqa
from app.models.price_history import PriceHistory, PriceStatistics  # noqa