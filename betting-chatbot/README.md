# Betting Chatbot

A sports betting chatbot that provides betting advice and parlay calculations.

## Features

- User authentication (register, login, logout)
- Chat interface with AI-powered betting advice
- Parlay calculator for calculating odds and expected value
- User profile management
- Free and premium tiers with different limits

## Setup

### Prerequisites

- Python 3.8+
- Node.js 14+
- npm or yarn
- OpenAI API key

### Environment Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/betting-chatbot.git
   cd betting-chatbot
   ```

2. Set up your OpenAI API key:
   ```
   python scripts/setup_openai.py
   ```
   Follow the prompts to enter your OpenAI API key. You can get an API key from [OpenAI's platform](https://platform.openai.com/api-keys).

3. Alternatively, you can manually update the `.env` files:
   - Root `.env` file
   - `web/backend/.env` file
   - `web/frontend/.env` file

   Set the `OPENAI_API_KEY` value in each file to your API key.

### Running the Application

Run the application using the provided script:

```
./run_local.sh
```

This will:
1. Start the Flask backend server on port 8080
2. Start the React frontend server on port 3080
3. Initialize the database if it doesn't exist

You can then access the application at http://localhost:3080

## Development

### Backend

The backend is built with Flask and uses:
- SQLite for the database
- OpenAI API for generating chat responses
- JWT for authentication

Key files:
- `app/__init__.py`: Application initialization
- `app/routes.py`: API endpoints
- `app/auth.py`: Authentication functions
- `app/database/db.py`: Database functions

### Frontend

The frontend is built with React and uses:
- TypeScript for type safety
- Material-UI for components
- Axios for API requests
- React Router for routing

Key files:
- `src/App.tsx`: Main application component
- `src/context/AuthContext.tsx`: Authentication context
- `src/pages/`: Page components
- `src/components/`: Reusable components

## Testing

### Backend Testing

Run the authentication test script:

```
cd web/backend
python test_auth.py
```

### Frontend Testing

Run the frontend tests:

```
cd web/frontend
npm test
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
