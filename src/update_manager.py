"""
Update Manager - Handles software updates with backup and rollback.
"""
import logging
import subprocess
import shutil
import os
from typing import Tuple, Optional
from pathlib import Path
from datetime import datetime


class UpdateManager:
    """Manages software updates via Git with safety features."""
    
    def __init__(self, repo_path: str, backup_enabled: bool = True):
        """
        Initialize update manager.
        
        Args:
            repo_path: Path to Git repository
            backup_enabled: Enable automatic backups before updates
        """
        self.logger = logging.getLogger(__name__)
        self.repo_path = Path(repo_path)
        self.backup_enabled = backup_enabled
        self.backup_dir = self.repo_path / 'backups'
        
        # Create backup directory
        if self.backup_enabled:
            self.backup_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"Update manager initialized for {repo_path}")
    
    def update_software(self, branch: str = 'main', 
                       test_after_update: bool = True,
                       rollback_on_fail: bool = True) -> Tuple[bool, str]:
        """
        Update software from Git repository.
        
        Args:
            branch: Git branch to pull from
            test_after_update: Run smoke tests after update
            rollback_on_fail: Automatically rollback if tests fail
            
        Returns:
            Tuple of (success, message)
        """
        try:
            self.logger.info(f"Starting software update from branch: {branch}")
            
            # 1. Backup current version
            if self.backup_enabled:
                backup_path = self._create_backup()
                if not backup_path:
                    return False, "Backup failed"
                self.logger.info(f"Backup created: {backup_path}")
            
            # 2. Get current commit for potential rollback
            current_commit = self._get_current_commit()
            
            # 3. Fetch and pull updates
            if not self._git_pull(branch):
                if self.backup_enabled:
                    self._restore_backup(backup_path)
                return False, "Git pull failed"
            
            # 4. Update dependencies
            if not self._update_dependencies():
                self.logger.warning("Dependencies update had warnings")
            
            # 5. Run smoke tests if enabled
            if test_after_update:
                if not self._run_smoke_tests():
                    self.logger.error("Smoke tests failed")
                    
                    if rollback_on_fail:
                        self.logger.info("Rolling back due to test failure")
                        success, msg = self.rollback(current_commit)
                        return False, f"Tests failed, rolled back: {msg}"
                    else:
                        return False, "Tests failed, no rollback"
            
            new_commit = self._get_current_commit()
            self.logger.info(f"✓ Software updated successfully: {current_commit} → {new_commit}")
            
            return True, f"Updated from {current_commit} to {new_commit}"
            
        except Exception as e:
            self.logger.error(f"Update error: {e}")
            return False, str(e)
    
    def rollback(self, target_commit: str = 'previous') -> Tuple[bool, str]:
        """
        Rollback to a previous commit.
        
        Args:
            target_commit: Commit hash to rollback to, or 'previous' for HEAD~1
            
        Returns:
            Tuple of (success, message)
        """
        try:
            current_commit = self._get_current_commit()
            
            if target_commit == 'previous':
                target_commit = 'HEAD~1'
            
            self.logger.info(f"Rolling back from {current_commit} to {target_commit}")
            
            # Git checkout target commit
            result = subprocess.run(
                ['git', 'checkout', target_commit],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return False, f"Git checkout failed: {result.stderr}"
            
            # Update dependencies
            self._update_dependencies()
            
            new_commit = self._get_current_commit()
            self.logger.info(f"✓ Rollback successful: {current_commit} → {new_commit}")
            
            return True, f"Rolled back to {new_commit}"
            
        except Exception as e:
            self.logger.error(f"Rollback error: {e}")
            return False, str(e)
    
    def _create_backup(self) -> Optional[Path]:
        """Create backup of current codebase."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            commit = self._get_current_commit()
            backup_name = f"backup_{timestamp}_{commit}.tar.gz"
            backup_path = self.backup_dir / backup_name
            
            # Create tarball (exclude backups, data, logs, venv)
            result = subprocess.run([
                'tar', '-czf', str(backup_path),
                '--exclude=backups',
                '--exclude=data',
                '--exclude=logs',
                '--exclude=venv',
                '--exclude=__pycache__',
                '--exclude=*.pyc',
                '-C', str(self.repo_path.parent),
                self.repo_path.name
            ], capture_output=True)
            
            if result.returncode == 0:
                self.logger.info(f"Backup created: {backup_path}")
                
                # Cleanup old backups (keep last 5)
                self._cleanup_old_backups(keep=5)
                
                return backup_path
            else:
                self.logger.error(f"Backup failed: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return None
    
    def _restore_backup(self, backup_path: Path) -> bool:
        """Restore from backup."""
        try:
            self.logger.info(f"Restoring from backup: {backup_path}")
            
            # Extract backup
            result = subprocess.run([
                'tar', '-xzf', str(backup_path),
                '-C', str(self.repo_path.parent)
            ], capture_output=True)
            
            if result.returncode == 0:
                self.logger.info("Backup restored successfully")
                return True
            else:
                self.logger.error(f"Restore failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error restoring backup: {e}")
            return False
    
    def _cleanup_old_backups(self, keep: int = 5):
        """Delete old backup files, keeping only the most recent."""
        try:
            backups = sorted(self.backup_dir.glob('backup_*.tar.gz'), 
                           key=lambda p: p.stat().st_mtime,
                           reverse=True)
            
            for backup in backups[keep:]:
                backup.unlink()
                self.logger.info(f"Deleted old backup: {backup.name}")
                
        except Exception as e:
            self.logger.error(f"Error cleaning up backups: {e}")
    
    def _git_pull(self, branch: str) -> bool:
        """Pull updates from Git repository."""
        try:
            # Fetch updates
            result = subprocess.run(
                ['git', 'fetch', 'origin'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error(f"Git fetch failed: {result.stderr}")
                return False
            
            # Checkout branch
            result = subprocess.run(
                ['git', 'checkout', branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error(f"Git checkout failed: {result.stderr}")
                return False
            
            # Pull updates
            result = subprocess.run(
                ['git', 'pull', 'origin', branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.logger.error(f"Git pull failed: {result.stderr}")
                return False
            
            self.logger.info(f"Git pull successful from {branch}")
            return True
            
        except Exception as e:
            self.logger.error(f"Git pull error: {e}")
            return False
    
    def _update_dependencies(self) -> bool:
        """Update Python dependencies."""
        try:
            # Check if venv exists
            venv_python = self.repo_path / 'venv' / 'bin' / 'python3'
            requirements = self.repo_path / 'requirements.txt'
            
            if not venv_python.exists():
                self.logger.warning("Virtual environment not found")
                return False
            
            if not requirements.exists():
                self.logger.warning("requirements.txt not found")
                return True  # Not critical
            
            # Update dependencies
            result = subprocess.run(
                [str(venv_python), '-m', 'pip', 'install', '-r', str(requirements), '--upgrade'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.logger.info("Dependencies updated successfully")
                return True
            else:
                self.logger.warning(f"Dependencies update warnings: {result.stderr}")
                return True  # Non-critical
                
        except Exception as e:
            self.logger.error(f"Error updating dependencies: {e}")
            return False
    
    def _run_smoke_tests(self) -> bool:
        """Run basic smoke tests."""
        try:
            self.logger.info("Running smoke tests...")
            
            venv_python = self.repo_path / 'venv' / 'bin' / 'python3'
            
            # Test 1: Import main modules
            test_imports = [
                'import src.sensor_manager',
                'import src.mqtt_client',
                'import src.buffer_manager',
                'import drivers'
            ]
            
            for test in test_imports:
                result = subprocess.run(
                    [str(venv_python), '-c', test],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    self.logger.error(f"Smoke test failed: {test}")
                    self.logger.error(result.stderr)
                    return False
            
            self.logger.info("✓ Smoke tests passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Smoke test error: {e}")
            return False
    
    def _get_current_commit(self) -> str:
        """Get current Git commit hash."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return 'unknown'
                
        except Exception as e:
            self.logger.error(f"Error getting commit: {e}")
            return 'unknown'
    
    def get_update_info(self) -> dict:
        """Get information about available updates."""
        try:
            # Fetch latest
            subprocess.run(
                ['git', 'fetch', 'origin'],
                cwd=self.repo_path,
                capture_output=True
            )
            
            # Get current and remote commits
            current = self._get_current_commit()
            
            result = subprocess.run(
                ['git', 'rev-parse', '--short', 'origin/main'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            remote = result.stdout.strip() if result.returncode == 0 else 'unknown'
            
            # Check if update available
            update_available = current != remote
            
            return {
                'current_commit': current,
                'remote_commit': remote,
                'update_available': update_available
            }
            
        except Exception as e:
            self.logger.error(f"Error getting update info: {e}")
            return {}
