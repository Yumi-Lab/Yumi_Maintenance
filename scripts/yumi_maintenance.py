import sqlite3
import os
from datetime import datetime, timedelta

class YumiMaintenance:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.active_prompts = set()
        self.prompt_queue = []
        self.is_showing_prompt = False
        self.printer_start_time = datetime.now()

        # File configuration
        self.db_file = "/home/pi/printer_data/database/yumi_maintenance.db"
        self.log_file = "/home/pi/printer_data/logs/yumi_maintenance.log"

        self.maintenance_tasks = self.init_tasks()
        self.init_db()
        self.load_history()
        self.init_gcode_commands()

        self.printer.register_event_handler("klippy:ready", self.handle_ready)
        self.log_event(f"=== Module initialized at {self.printer_start_time} ===")

    def init_db(self):
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS maintenance_history
                     (name TEXT PRIMARY KEY,
                      last_done TEXT,
                      next_check TEXT,
                      first_done INTEGER DEFAULT 0)''')
        conn.commit()
        conn.close()

    def init_tasks(self):
        return [
            {
                'name': 'oil_xy_axes',
                'interval': timedelta(month=1),
                'message': "Lubricate X/Y axes",
                'prompt': "Code: A00 - MAINTENANCE: Lubricate X/Y axes (Monthly) Scan for complete guide",
                'qr_message': "Scan for complete guide",
                'imgqr': "/home/pi/KlipperScreen/styles/maintenance/xyz.png",
                'priority': 1,
                'first': True,
                'first_delay': timedelta(seconds=90)
            },
            {
                'name': 'oil_z_axes',
                'interval': timedelta(month=1),
                'message': "Lubricate Z axes",
                'prompt': "Code: A00 - MAINTENANCE: Lubricate Z axes (Monthly) Scan for complete guide",
                'qr_message': "Scan for complete guide",
                'imgqr': "/home/pi/KlipperScreen/styles/maintenance/xyz.png",
                'priority': 1,
                'first': True,
                'first_delay': timedelta(seconds=90)
            },
            {
                'name': 'clean_nozzle',
                'interval': timedelta(week=2),
                'message': "Clean nozzle",
                'prompt': "Code: E00 - MAINTENANCE: Clean nozzle (Weekly) Scan for complete guide",
                'qr_message': "Cleaning guide",
                'imgqr': "/home/pi/KlipperScreen/styles/maintenance/noozle.png",
                'priority': 2,
                'first': False,
                'first_delay': timedelta(seconds=90)
            }
            {
                'name': 'clean_plate',
                'interval': timedelta(week=2),
                'message': "Clean Plate",
                'prompt': "Code: P00 - MAINTENANCE: Clean Plate (Weekly) Scan for complete guide",
                'qr_message': "Cleaning guide",
                'imgqr': "/home/pi/KlipperScreen/styles/maintenance/plate.png",
                'priority': 2,
                'first': False,
                'first_delay': timedelta(seconds=90)
            }
            {
                'name': 'belt_tension',
                'interval': timedelta(week=2),
                'message': "Clean Plate",
                'prompt': "Code: A01 - MAINTENANCE: Belt Tension (Weekly) Scan for complete guide",
                'qr_message': "Cleaning guide",
                'imgqr': "/home/pi/KlipperScreen/styles/belt_tension.png",
                'priority': 2,
                'first': False,
                'first_delay': timedelta(seconds=90)
            }
        ]

    def log_event(self, message):
        """Detailed logging with standardized format"""
        log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")
        print(log_entry)  # Also show in Klipper console

    def load_history(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        now = datetime.now()

        for task in self.maintenance_tasks:
            c.execute("SELECT last_done, next_check, first_done FROM maintenance_history WHERE name=?", (task['name'],))
            result = c.fetchone()

            if result:
                task['last_done'] = datetime.fromisoformat(result[0]) if result[0] else None
                task['next_check'] = datetime.fromisoformat(result[1]) if result[1] else now + task['interval']
                task['first_done'] = bool(result[2])
                self.log_event(f"Loaded history - {task['name']}: last done {task['last_done']}, next due {task['next_check']}")
            else:
                task['last_done'] = None
                task['next_check'] = now + task['interval']
                task['first_done'] = False
                c.execute("INSERT INTO maintenance_history (name, last_done, next_check, first_done) VALUES (?, ?, ?, ?)",
                         (task['name'], None, task['next_check'].isoformat(), 0))
                self.log_event(f"New task registered - {task['name']}: first due {task['next_check']}")

        conn.commit()
        conn.close()

    def save_history(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        for task in self.maintenance_tasks:
            c.execute('''INSERT OR REPLACE INTO maintenance_history
                         (name, last_done, next_check, first_done)
                         VALUES (?, ?, ?, ?)''',
                     (task['name'],
                      task['last_done'].isoformat() if task['last_done'] else None,
                      task['next_check'].isoformat(),
                      int(task.get('first_done', False))))
        conn.commit()
        conn.close()

    def show_prompt(self, task):
        if task['name'] in self.active_prompts or self.is_showing_prompt:
            self.prompt_queue.append(task)
            self.log_event(f"Task queued: {task['name']}")
            return
            
        self.active_prompts.add(task['name'])
        self.is_showing_prompt = True
        self.log_event(f"Displaying maintenance prompt: {task['name']}")
        
        
        img_part = f'RESPOND TYPE=command MSG="action:prompt_image {task["imgqr"]}"\n' if 'imgqr' in task else ''
        
        gcode_script = f"""
        RESPOND TYPE=command MSG="action:prompt_begin Maintenance Required"
        RESPOND TYPE=command MSG="action:prompt_text {task['prompt']}"
        {img_part}
	RESPOND TYPE=command MSG="action:prompt_footer_button Not Now|MAINTENANCE_POSTPONE TASK={task['name']}"
        RESPOND TYPE=command MSG="action:prompt_footer_button Confirm|MAINTENANCE_CONFIRM TASK={task['name']}"
        RESPOND TYPE=command MSG="action:prompt_close_on_click"
        RESPOND TYPE=command MSG="action:prompt_show"
        """
        self.gcode.run_script_from_command(gcode_script)

    def handle_ready(self):
        """Schedule display after 1 minute 30"""
        for task in self.maintenance_tasks:
            if task.get('first', False) and not task.get('first_done', False):
                delay = task['first_delay'].total_seconds()
                self.reactor.register_timer(
                    lambda e, t=task: self._trigger_prompt(t),
                    self.reactor.monotonic() + delay
                )
                self.log_event(f"Task '{task['name']}' scheduled in {delay} seconds")

    def _trigger_prompt(self, task):
        """Trigger for delayed display"""
        if not task.get('first_done', False):
            self.show_prompt(task)
        return self.reactor.NEVER

    def _next_prompt(self):
        """Show next prompt in queue"""
        self.is_showing_prompt = False
        if self.prompt_queue:
            task = self.prompt_queue.pop(0)
            self.show_prompt(task)

    def cmd_postpone_maintenance(self, gcmd):
        task_name = gcmd.get('TASK')
        if task_name in self.active_prompts:
            self.active_prompts.remove(task_name)
            self.gcode.run_script_from_command('RESPOND TYPE=command MSG="action:prompt_end"')
            self.log_event(f"MAINTENANCE POSTPONED - Task: {task_name}, Reason: User selected 'Postpone'")
            gcmd.respond_info(f"Maintenance {task_name} postponed.")
            self.reactor.register_callback(lambda e: self._next_prompt())
        else:
            self.log_event(f"POSTPONE ATTEMPT FAILED - No active prompt for: {task_name}")
            gcmd.respond_info("No active prompt for this task")

    def cmd_confirm_maintenance(self, gcmd):
        task_name = gcmd.get('TASK')
        if task_name in self.active_prompts:
            self.active_prompts.remove(task_name)
            now = datetime.now()
            for task in self.maintenance_tasks:
                if task['name'] == task_name:
                    previous_last_done = task['last_done']
                    task['last_done'] = now
                    task['next_check'] = now + task['interval']
                    task['first_done'] = True
                    self.save_history()
                    
                    # Detailed logging
                    log_details = [
                        f"MAINTENANCE CONFIRMED - Task: {task_name}",
                        f"Completion date: {now.strftime('%Y-%m-%d %H:%M:%S')}",
                        f"Previous completion: {previous_last_done.strftime('%Y-%m-%d %H:%M:%S') if previous_last_done else 'First completion'}",
                        f"Next due: {task['next_check'].strftime('%Y-%m-%d %H:%M:%S')}"
                    ]
                    self.log_event("\n  ".join(log_details))
                    
                    break
            
            self.gcode.run_script_from_command('RESPOND TYPE=command MSG="action:prompt_end"')
            gcmd.respond_info(f"Maintenance {task_name} confirmed.")
            self.reactor.register_callback(lambda e: self._next_prompt())
        else:
            self.log_event(f"CONFIRM ATTEMPT FAILED - No active prompt for: {task_name}")
            gcmd.respond_info("No active prompt for this task")

    def cmd_maintenance_status(self, gcmd):
        now = datetime.now()
        output = ["Maintenance status:"]
        
        for task in sorted(self.maintenance_tasks, key=lambda x: x['priority']):
            status = "? Up to date" if now < task['next_check'] else "?? Required"
            last_done = f"last done: {task['last_done'].strftime('%Y-%m-%d %H:%M:%S')}" if task['last_done'] else "never done"
            next_check = task['next_check'].strftime('%Y-%m-%d %H:%M:%S')
            output.append(f"{task['name']}: {status} ({last_done}, next due: {next_check})")
        
        full_status = "\n".join(output)
        self.log_event(f"STATUS REQUESTED:\n{full_status}")
        gcmd.respond_info(full_status)

    def cmd_reset_maintenance(self, gcmd):
        """Reset maintenance history for all tasks"""
        try:
            # Clear all active prompts
            self.active_prompts.clear()
            self.prompt_queue.clear()
            self.is_showing_prompt = False
            
            # Reset database
            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()
            c.execute("DELETE FROM maintenance_history")
            conn.commit()
            conn.close()
        
            
            # Reload with fresh state
            now = datetime.now()
            for task in self.maintenance_tasks:
                task['last_done'] = None
                task['next_check'] = now + task['interval']
                task['first_done'] = False
            
            self.save_history()
            self.log_event("MAINTENANCE SYSTEM RESET - All history cleared")
            gcmd.respond_info("Maintenance system reset complete. All history cleared.")
        except Exception as e:
            self.log_event(f"RESET FAILED: {str(e)}")
            gcmd.respond_error(f"Maintenance reset failed: {str(e)}")

    def init_gcode_commands(self):
        self.gcode.register_command("MAINTENANCE_POSTPONE", self.cmd_postpone_maintenance,
                                  desc="Postpone a maintenance task")
        self.gcode.register_command("MAINTENANCE_CONFIRM", self.cmd_confirm_maintenance,
                                  desc="Confirm maintenance was completed")
        self.gcode.register_command("MAINTENANCE_STATUS", self.cmd_maintenance_status,
                                  desc="Show detailed maintenance status")
        self.gcode.register_command("MAINTENANCE_RESET", self.cmd_reset_maintenance,
                                  desc="Reset all maintenance history")

def load_config(config):
    return YumiMaintenance(config)