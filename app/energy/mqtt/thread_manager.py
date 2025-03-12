# energy/mqtt/thread_manager.py
"""
Gestore centralizzato per i thread dell'applicazione.
Da utilizzare per tutti i thread che necessitano di essere tracciati e terminati correttamente.
"""
import logging
import threading
import time
from typing import Dict, Callable, Optional, List, Any, Tuple

logger = logging.getLogger('energy.mqtt')

class ThreadManager:
    """Gestore centralizzato per i thread dell'applicazione"""
    
    def __init__(self):
        self._threads: Dict[str, Tuple[threading.Thread, float]] = {}
        self._lock = threading.Lock()
        self._running = True
        
        # Avvia thread monitor
        self._monitor_thread = threading.Thread(
            target=self._monitor_threads,
            daemon=True,
            name="thread_monitor"
        )
        self._monitor_thread.start()
    
    def start_thread(self, name: str, target: Callable, 
                   daemon: bool = True, args: tuple = (), 
                   kwargs: Optional[Dict[str, Any]] = None) -> bool:
        """
        Avvia un thread con gestione delle eccezioni e tracciamento
        
        Args:
            name: Nome univoco del thread
            target: Funzione target da eseguire
            daemon: Se il thread è daemon
            args: Argomenti posizionali per la funzione target
            kwargs: Argomenti keyword per la funzione target
            
        Returns:
            bool: True se il thread è stato avviato, False altrimenti
        """
        if kwargs is None:
            kwargs = {}
        
        def thread_wrapper():
            try:
                logger.debug(f"Thread {name} starting")
                target(*args, **(kwargs or {}))
                logger.debug(f"Thread {name} completed normally")
            except Exception as e:
                logger.error(f"Thread {name} failed with exception: {str(e)}", exc_info=True)
            finally:
                with self._lock:
                    self._threads.pop(name, None)
        
        with self._lock:
            # Ferma thread precedente con stesso nome se esiste
            if name in self._threads and self._threads[name][0].is_alive():
                logger.warning(f"Thread {name} already running, not starting new instance")
                return False
            
            thread = threading.Thread(target=thread_wrapper, daemon=daemon, name=name)
            self._threads[name] = (thread, time.time())
            thread.start()
            logger.debug(f"Thread {name} started")
            return True
    
    def stop_thread(self, name: str, timeout: float = 2.0) -> bool:
        """
        Attende la terminazione di un thread specifico
        
        Args:
            name: Nome del thread da fermare
            timeout: Timeout in secondi per l'attesa
            
        Returns:
            bool: True se il thread è stato fermato, False altrimenti
        """
        with self._lock:
            if name not in self._threads:
                return False
            
            thread, _ = self._threads[name]
        
        if thread.is_alive():
            logger.debug(f"Waiting for thread {name} to terminate (timeout: {timeout}s)")
            thread.join(timeout=timeout)
            if thread.is_alive():
                logger.warning(f"Thread {name} did not terminate within timeout")
                return False
        
        with self._lock:
            self._threads.pop(name, None)
        return True
    
    def stop_all(self, timeout: float = 2.0) -> bool:
        """
        Attende la terminazione ordinata di tutti i thread
        
        Args:
            timeout: Timeout in secondi per l'attesa di ciascun thread
            
        Returns:
            bool: True se tutti i thread sono stati fermati, False altrimenti
        """
        self._running = False
        
        with self._lock:
            active_threads = list(self._threads.items())
        
        all_stopped = True
        for name, (thread, _) in active_threads:
            if thread.is_alive():
                logger.debug(f"Waiting for thread {name} to terminate (timeout: {timeout}s)")
                thread.join(timeout=timeout)
                if thread.is_alive():
                    logger.warning(f"Thread {name} did not terminate within timeout")
                    all_stopped = False
                else:
                    with self._lock:
                        self._threads.pop(name, None)
        
        return all_stopped
    
    def get_active_threads(self) -> List[Dict[str, Any]]:
        """
        Restituisce informazioni sui thread attivi
        
        Returns:
            List[Dict[str, Any]]: Lista di informazioni sui thread attivi
        """
        with self._lock:
            return [
                {
                    'name': name,
                    'alive': thread.is_alive(),
                    'daemon': thread.daemon,
                    'started': start_time,
                    'running_time': time.time() - start_time
                }
                for name, (thread, start_time) in self._threads.items()
            ]
    
    def _monitor_threads(self):
        """Thread monitor per identificare thread zombie o bloccati"""
        check_interval = 60  # Controlla ogni minuto
        
        while self._running:
            try:
                with self._lock:
                    current_time = time.time()
                    for name, (thread, start_time) in list(self._threads.items()):
                        # Thread attivo da più di 2 ore
                        if thread.is_alive() and (current_time - start_time) > 7200:
                            logger.warning(f"Thread {name} running for over 2 hours")
                        
                        # Thread non più attivo ma ancora tracciato
                        if not thread.is_alive():
                            self._threads.pop(name, None)
                            logger.debug(f"Removed dead thread {name} from tracking")
            except Exception as e:
                logger.error(f"Error in thread monitor: {str(e)}")
            
            # Pausa tra controlli
            for _ in range(check_interval):
                if not self._running:
                    break
                time.sleep(1)

# Istanza singleton del gestore thread
thread_manager = ThreadManager()