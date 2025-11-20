"""
External Event Filter
Halts trading during major external events (RBI announcements, elections, etc.)
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import EXTERNAL_EVENTS_FILE, TRADING_HALT_ON_EVENTS


class ExternalEventFilter:
    """
    Filters trading based on external events
    Can halt trading during major announcements or events
    """
    
    def __init__(self, events_file: Optional[Path] = None):
        """
        Initialize External Event Filter
        
        Args:
            events_file: Path to external events JSON file
        """
        self.events_file = events_file or EXTERNAL_EVENTS_FILE
        self.events: List[Dict] = []
        self.enabled = TRADING_HALT_ON_EVENTS
        
        self._load_events()
    
    def _load_events(self):
        """Load external events from file"""
        if self.events_file.exists():
            try:
                with open(self.events_file, 'r') as f:
                    self.events = json.load(f)
                logger.info(f"Loaded {len(self.events)} external events")
            except Exception as e:
                logger.error(f"Error loading external events: {e}")
                self.events = []
        else:
            # Create sample events file
            self._create_sample_events_file()
    
    def _create_sample_events_file(self):
        """Create sample external events file"""
        sample_events = [
            {
                "name": "RBI Monetary Policy Meeting",
                "date": "2024-12-06",
                "start_time": "10:00",
                "end_time": "12:00",
                "type": "RBI_ANNOUNCEMENT",
                "halt_trading": True
            },
            {
                "name": "General Election Results",
                "date": "2024-06-04",
                "start_time": "08:00",
                "end_time": "18:00",
                "type": "ELECTION",
                "halt_trading": True
            },
            {
                "name": "Budget Announcement",
                "date": "2025-02-01",
                "start_time": "11:00",
                "end_time": "13:00",
                "type": "BUDGET",
                "halt_trading": True
            }
        ]
        
        try:
            with open(self.events_file, 'w') as f:
                json.dump(sample_events, f, indent=2)
            logger.info(f"Created sample external events file: {self.events_file}")
            self.events = sample_events
        except Exception as e:
            logger.error(f"Error creating sample events file: {e}")
    
    def should_halt_trading(self) -> bool:
        """
        Check if trading should be halted due to external events
        
        Returns:
            True if trading should be halted, False otherwise
        """
        if not self.enabled:
            return False
        
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()
        
        for event in self.events:
            if not event.get('halt_trading', False):
                continue
            
            event_date_str = event.get('date')
            if not event_date_str:
                continue
            
            try:
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
                
                # Check if event is today
                if event_date != current_date:
                    continue
                
                # Check if current time is within event window
                start_time_str = event.get('start_time', '00:00')
                end_time_str = event.get('end_time', '23:59')
                
                start_time = datetime.strptime(start_time_str, "%H:%M").time()
                end_time = datetime.strptime(end_time_str, "%H:%M").time()
                
                if start_time <= current_time <= end_time:
                    logger.warning(
                        f"Trading halted due to external event: {event.get('name')} "
                        f"({event.get('type')})"
                    )
                    return True
            
            except Exception as e:
                logger.error(f"Error parsing event {event}: {e}")
                continue
        
        return False
    
    def add_event(self, name: str, date: str, start_time: str, end_time: str,
                  event_type: str, halt_trading: bool = True):
        """
        Add an external event
        
        Args:
            name: Event name
            date: Event date (YYYY-MM-DD)
            start_time: Start time (HH:MM)
            end_time: End time (HH:MM)
            event_type: Event type
            halt_trading: Whether to halt trading during this event
        """
        event = {
            "name": name,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
            "type": event_type,
            "halt_trading": halt_trading
        }
        
        self.events.append(event)
        self._save_events()
        logger.info(f"Added external event: {name}")
    
    def _save_events(self):
        """Save events to file"""
        try:
            with open(self.events_file, 'w') as f:
                json.dump(self.events, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving events: {e}")
    
    def get_upcoming_events(self, days: int = 7) -> List[Dict]:
        """
        Get upcoming events within specified days
        
        Args:
            days: Number of days to look ahead
            
        Returns:
            List of upcoming events
        """
        now = datetime.now()
        upcoming = []
        
        for event in self.events:
            event_date_str = event.get('date')
            if not event_date_str:
                continue
            
            try:
                event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
                days_until = (event_date - now.date()).days
                
                if 0 <= days_until <= days:
                    upcoming.append(event)
            except Exception as e:
                logger.error(f"Error parsing event date: {e}")
        
        return sorted(upcoming, key=lambda x: x.get('date', ''))
