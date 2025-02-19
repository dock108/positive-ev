import pytest
from unittest.mock import patch
from app.models import Bet, BetResult
from app import db

def test_trigger_scrape(client):
    """Test the scrape trigger endpoint."""
    with patch('app.scraper.services.ScraperService.scrape_odds') as mock_scrape:
        mock_scrape.return_value = [
            Bet(
                bet_id='test_bet_1',
                timestamp='2024-02-15 20:00:00',
                ev_percent=5.2,
                event_time='2024-02-15 20:00:00',
                event_teams='Lakers vs Warriors',
                sport_league='NBA',
                bet_type='Moneyline',
                description='Lakers to win',
                odds=150,
                sportsbook='DraftKings'
            )
        ]
        
        response = client.post('/scrape')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['new_bets']) == 1
        assert data['new_bets'][0]['bet_id'] == 'test_bet_1'

def test_scrape_failure(client):
    """Test scraping failure handling."""
    with patch('app.scraper.services.ScraperService.scrape_odds') as mock_scrape:
        mock_scrape.side_effect = Exception('Scraping failed')
        
        response = client.post('/scrape')
        assert response.status_code == 500
        
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Scraping failed' in data['message']

def test_scrape_status(client, sample_bet):
    """Test the scrape status endpoint."""
    response = client.get('/scrape/status')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['total_bets'] == 1
    assert data['unresolved_bets'] == 1
    assert 'last_update' in data

def test_empty_scrape_status(client):
    """Test scrape status with no data."""
    response = client.get('/scrape/status')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'unknown'
    assert data['last_update'] is None

def test_update_results(client, sample_bet):
    """Test the results update endpoint."""
    with patch('app.scraper.services.ScraperService.update_bet_results') as mock_update:
        mock_update.return_value = [sample_bet]
        
        response = client.post('/scrape/results')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'success'
        assert len(data['updated_bets']) == 1

def test_update_results_failure(client):
    """Test results update failure handling."""
    with patch('app.scraper.services.ScraperService.update_bet_results') as mock_update:
        mock_update.side_effect = Exception('Update failed')
        
        response = client.post('/scrape/results')
        assert response.status_code == 500
        
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Update failed' in data['message']

def test_cleanup_old_data(client, sample_bet):
    """Test the cleanup endpoint."""
    with patch('app.scraper.services.ScraperService.cleanup_old_data') as mock_cleanup:
        mock_cleanup.return_value = 1
        
        response = client.post('/scrape/cleanup')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'success'
        assert data['cleaned_count'] == 1
        assert data['backup_created'] is True

def test_cleanup_failure(client):
    """Test cleanup failure handling."""
    with patch('app.scraper.services.ScraperService.cleanup_old_data') as mock_cleanup:
        mock_cleanup.side_effect = Exception('Cleanup failed')
        
        response = client.post('/scrape/cleanup')
        assert response.status_code == 500
        
        data = response.get_json()
        assert data['status'] == 'error'
        assert 'Cleanup failed' in data['message'] 