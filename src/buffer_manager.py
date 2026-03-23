"""
Buffer Manager - Local SQLite database for resilient data storage.
"""
import sqlite3
import json
import logging
import time
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta


class BufferManager:
    """Manages local SQLite buffer for sensor readings."""
    
    def __init__(self, db_path: str, max_records: int = 70000, cleanup_days: int = 7):
        """
        Initialize buffer manager.
        
        Args:
            db_path: Path to SQLite database file
            max_records: Maximum records to keep
            cleanup_days: Days to keep old records
        """
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.max_records = max_records
        self.cleanup_days = cleanup_days
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Create database tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create readings buffer table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS readings_buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    machine_id INTEGER NOT NULL,
                    company_id INTEGER NOT NULL,
                    sensor_id INTEGER NOT NULL,
                    sensor_name TEXT,
                    sensor_type TEXT,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    metadata TEXT,
                    transmitted INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    transmitted_at TEXT
                )
            ''')
            
            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_transmitted 
                ON readings_buffer(transmitted)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON readings_buffer(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_machine_sensor 
                ON readings_buffer(machine_id, sensor_id)
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    def save_reading(self, reading_data: Dict[str, Any]) -> bool:
        """
        Save a single reading to buffer.
        
        Args:
            reading_data: Dictionary with reading data
            
        Returns:
            True if saved successfully
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = reading_data.get('timestamp')
            machine_id = reading_data.get('machine_id')
            company_id = reading_data.get('company_id')
            
            # Insert each sensor reading
            for reading in reading_data.get('readings', []):
                sensor_id = reading.get('sensor_id')
                sensor_name = reading.get('sensor_name')
                sensor_type = reading.get('type')
                
                # Extract main value based on sensor type
                data = reading.get('data', {})
                
                if sensor_type == 'vibration':
                    # Store RMS for each axis
                    for axis in ['x', 'y', 'z']:
                        if axis in data:
                            cursor.execute('''
                                INSERT INTO readings_buffer 
                                (timestamp, machine_id, company_id, sensor_id, 
                                 sensor_name, sensor_type, value, unit, metadata)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                datetime.fromtimestamp(timestamp).isoformat(),
                                machine_id,
                                company_id,
                                sensor_id,
                                f"{sensor_name} - {axis.upper()}",
                                sensor_type,
                                data[axis],
                                data.get('unit', 'g'),
                                json.dumps({'axis': axis})
                            ))
                
                elif sensor_type == 'temperature':
                    cursor.execute('''
                        INSERT INTO readings_buffer 
                        (timestamp, machine_id, company_id, sensor_id, 
                         sensor_name, sensor_type, value, unit, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        datetime.fromtimestamp(timestamp).isoformat(),
                        machine_id,
                        company_id,
                        sensor_id,
                        sensor_name,
                        sensor_type,
                        data.get('temperature', 0),
                        data.get('unit', 'celsius'),
                        json.dumps({'internal_temp': data.get('internal_temp')})
                    ))
                
                elif sensor_type == 'current':
                    cursor.execute('''
                        INSERT INTO readings_buffer 
                        (timestamp, machine_id, company_id, sensor_id, 
                         sensor_name, sensor_type, value, unit, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        datetime.fromtimestamp(timestamp).isoformat(),
                        machine_id,
                        company_id,
                        sensor_id,
                        sensor_name,
                        sensor_type,
                        data.get('current', 0),
                        data.get('unit', 'ampere'),
                        json.dumps({'voltage': data.get('voltage')})
                    ))
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving reading to buffer: {e}")
            return False
    
    def mark_transmitted(self, record_ids: List[int]) -> bool:
        """
        Mark records as transmitted.
        
        Args:
            record_ids: List of record IDs to mark
            
        Returns:
            True if successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            timestamp = datetime.utcnow().isoformat()
            
            cursor.executemany('''
                UPDATE readings_buffer 
                SET transmitted = 1, transmitted_at = ?
                WHERE id = ?
            ''', [(timestamp, record_id) for record_id in record_ids])
            
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Marked {len(record_ids)} records as transmitted")
            return True
            
        except Exception as e:
            self.logger.error(f"Error marking records as transmitted: {e}")
            return False
    
    def get_untransmitted_readings(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get readings that haven't been transmitted yet.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of reading dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM readings_buffer 
                WHERE transmitted = 0 
                ORDER BY timestamp ASC 
                LIMIT ?
            ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            readings = []
            for row in rows:
                reading = {
                    'id': row['id'],
                    'timestamp': row['timestamp'],
                    'machine_id': row['machine_id'],
                    'company_id': row['company_id'],
                    'sensor_id': row['sensor_id'],
                    'sensor_name': row['sensor_name'],
                    'sensor_type': row['sensor_type'],
                    'value': row['value'],
                    'unit': row['unit'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                }
                readings.append(reading)
            
            return readings
            
        except Exception as e:
            self.logger.error(f"Error getting untransmitted readings: {e}")
            return []
    
    def cleanup_old_records(self) -> int:
        """
        Delete old transmitted records.
        
        Returns:
            Number of records deleted
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Delete transmitted records older than cleanup_days
            cutoff_date = datetime.utcnow() - timedelta(days=self.cleanup_days)
            
            cursor.execute('''
                DELETE FROM readings_buffer 
                WHERE transmitted = 1 
                AND timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted > 0:
                self.logger.info(f"Cleaned up {deleted} old records")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old records: {e}")
            return 0
    
    def get_buffer_stats(self) -> Dict[str, Any]:
        """
        Get buffer statistics.
        
        Returns:
            Dictionary with buffer statistics
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total records
            cursor.execute('SELECT COUNT(*) FROM readings_buffer')
            total = cursor.fetchone()[0]
            
            # Untransmitted records
            cursor.execute('SELECT COUNT(*) FROM readings_buffer WHERE transmitted = 0')
            untransmitted = cursor.fetchone()[0]
            
            # Transmitted records
            cursor.execute('SELECT COUNT(*) FROM readings_buffer WHERE transmitted = 1')
            transmitted = cursor.fetchone()[0]
            
            # Oldest record
            cursor.execute('SELECT MIN(timestamp) FROM readings_buffer')
            oldest = cursor.fetchone()[0]
            
            # Database size
            cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
            db_size = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_records': total,
                'untransmitted': untransmitted,
                'transmitted': transmitted,
                'oldest_record': oldest,
                'database_size_mb': round(db_size / (1024 * 1024), 2),
                'capacity_used_percent': round((total / self.max_records) * 100, 1)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting buffer stats: {e}")
            return {}
