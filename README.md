# Aura - Personal Home & Property Assistant

A personal assistant AI that aggregates and organizes your home-related data from multiple sources (Gmail, WhatsApp, Bank, Google Drive) and allows conversational queries about your properties, expenses, and documents.

## Features

- **Property Management**: Track multiple properties with details and expenses
- **Data Integration**: Connect Gmail, WhatsApp, Bank accounts, and Google Drive
- **Conversational Interface**: Chat with your AI assistant about your properties
- **Expense Tracking**: Monitor rent, utilities, maintenance, and other property-related costs
- **Document Management**: Store and search through property-related documents

## Tech Stack

- **Backend**: Python with FastAPI
- **Frontend**: React with TypeScript and Material-UI
- **Database**: PostgreSQL
- **Authentication**: JWT tokens with bcrypt password hashing

## Getting Started

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL
- Redis (for background tasks)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. Set up the database:
   ```bash
   # Create PostgreSQL database
   createdb aura_db
   
   # Run the application to create tables
   python -m app.main
   ```

6. Start the backend server:
   ```bash
   uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm start
   ```

The frontend will be available at `http://localhost:3000`

## API Documentation

Once the backend is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
aura/
├── backend/
│   ├── app/
│   │   ├── core/           # Core configuration and security
│   │   ├── routers/        # API route handlers
│   │   ├── models.py       # Database models
│   │   ├── schemas.py      # Pydantic schemas
│   │   ├── database.py     # Database configuration
│   │   └── main.py         # FastAPI application
│   ├── requirements.txt    # Python dependencies
│   └── env.example        # Environment variables template
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── contexts/       # React contexts
│   │   ├── services/       # API services
│   │   ├── types/          # TypeScript types
│   │   └── theme.ts        # Material-UI theme
│   └── package.json
└── README.md
```



## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.
