import pytest
from flask import url_for
from app.models import Bet, BetResult

def test_index_route(client):
    """Test the index route."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Recent Bets' in response.data

def test_results_route(client, sample_bet, sample_bet_result):
    """Test the results route."""
    response = client.get('/results')
    assert response.status_code == 200
    assert b'Resolved Bets' in response.data
    assert b'Lakers vs Warriors' in response.data
    assert b'DraftKings' in response.data

def test_rankings_route(client, sample_bet):
    """Test the rankings route."""
    response = client.get('/rankings')
    assert response.status_code == 200
    assert b'Top Ranked Bets' in response.data
    assert b'Lakers vs Warriors' in response.data

def test_rankings_with_filters(client, sample_bet):
    """Test the rankings route with filters."""
    response = client.get('/rankings?sport=NBA&min_ev=5.0&sportsbook=DraftKings')
    assert response.status_code == 200
    assert b'Lakers vs Warriors' in response.data

    # Test with non-matching filters
    response = client.get('/rankings?sport=NFL&min_ev=10.0')
    assert response.status_code == 200
    assert b'Lakers vs Warriors' not in response.data

def test_trends_route(client, sample_bet, sample_bet_result):
    """Test the trends route."""
    response = client.get('/trends')
    assert response.status_code == 200
    assert b'EV Trends' in response.data

def test_trends_with_timeframe(client, sample_bet, sample_bet_result):
    """Test the trends route with timeframe filter."""
    response = client.get('/trends?timeframe=week&sport=NBA')
    assert response.status_code == 200
    assert b'EV Trends' in response.data

def test_pagination(client):
    """Test pagination on results page."""
    # Create multiple bets
    bets = []
    for i in range(60):  # Create 60 bets to test pagination
        bet = Bet(
            bet_id=f'test_bet_{i}',
            timestamp='2024-02-15 20:00:00',
            ev_percent=5.2,
            event_time='2024-02-15 20:00:00',
            event_teams=f'Team A vs Team B {i}',
            sport_league='NBA',
            bet_type='Moneyline',
            description='Test bet',
            odds=150,
            sportsbook='DraftKings',
            result='W'
        )
        bets.append(bet)
    
    db.session.bulk_save_objects(bets)
    db.session.commit()
    
    # Test first page
    response = client.get('/results?page=1')
    assert response.status_code == 200
    assert b'Team A vs Team B 0' in response.data
    
    # Test second page
    response = client.get('/results?page=2')
    assert response.status_code == 200
    assert b'Team A vs Team B 50' in response.data

def test_invalid_page(client):
    """Test invalid page number."""
    response = client.get('/results?page=999')
    assert response.status_code == 404

def test_cache_control(client):
    """Test cache headers are set correctly."""
    response = client.get('/trends')
    assert response.status_code == 200
    assert 'Cache-Control' in response.headers 