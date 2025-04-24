"""
TowerOfHanoiGame.py

An interactive Tower of Hanoi puzzle supporting up to 100 disks:
- Dynamic disk count (n ≥ 1) via user prompt.
- Responsive UI: disk height scales inversely with n (min 2px) to fit any number.
- Canvas rendering of three vertical towers and disks.
- Drag-and-drop ergonomics with move validation.
- Real-time win detection on any non-source tower.
- Automated simulation of the minimal solution using a generator for O(n) memory.

As a mathematician, we leverage the 2^n−1 move optimality.
As a game developer, we prioritize UX: instant feedback, reset flows, simulation.
"""
import tkinter as tk
from tkinter import simpledialog, messagebox

class TowerOfHanoiGame:
    """
    Encapsulates the Hanoi puzzle state and UI. Disks start on tower 0, goal is any other tower.
    Uses a generator-based simulation to handle large n without huge memory.
    """
    def __init__(self):
        self._start_game()

    def _start_game(self):
        # Prompt the player for disk count; enforce minimum of 1
        self.root = tk.Tk()
        self.root.title("Tower of Hanoi")
        self.num_disks = simpledialog.askinteger(
            "Disks", "Enter number of disks (>=1):", minvalue=1, parent=self.root)
        if not self.num_disks:
            self.root.destroy()
            return

        # Layout constants: canvas size and tower arrangement
        self.canvas_width = 1920
        self.canvas_height = 1080
        self.tower_count = 3
        self.tower_spacing = self.canvas_width // self.tower_count
        # Disk height scales so n=100 uses ~6px per disk
        self.disk_height = max(5, self.canvas_height // (self.num_disks * 3))

        # Set up UI
        self.canvas = tk.Canvas(self.root, width=self.canvas_width, height=self.canvas_height)
        self.canvas.pack()
        frame = tk.Frame(self.root)
        frame.place(x=10, y=10)
        tk.Button(frame, text="Reset", command=self.reset).pack(side=tk.LEFT, padx=5)
        tk.Button(frame, text="Simulation", command=self.simulation).pack(side=tk.LEFT)

        # Model: towers store stacks of (canvas_id, size)
        self.towers = [[] for _ in range(self.tower_count)]
        self._draw_towers()
        self._init_stacks()

        # Bind events for drag-and-drop on disk items
        self.drag_data = {"item": None, "x": 0, "y": 0, "from_tower": None}
        self.canvas.tag_bind("disk", "<ButtonPress-1>", self.on_ButtonPress_1)
        self.canvas.tag_bind("disk", "<B1-Motion>", self.on_B1_Motion)
        self.canvas.tag_bind("disk", "<ButtonRelease-1>", self.on_ButtonRelease_1)

        self.root.mainloop()

    def reset(self):
        """
        Fully restart the game: prompt for disk count again and reinitialize everything.
        """
        self.root.destroy()
        TowerOfHanoiGame()

    def _draw_towers(self):
        """Draw three vertical towers (lines) at equal spacing."""
        self.canvas.delete("all")
        y0 = self.canvas_height
        height = self.disk_height * (self.num_disks + 1)
        for i in range(self.tower_count):
            x = i * self.tower_spacing + self.tower_spacing // 2
            self.canvas.create_line(x, y0, x, y0 - height, width=5)

    def _init_stacks(self):
        """Clear model and create disks on tower 0 from largest (bottom) to smallest (top)."""
        self.towers = [[] for _ in range(self.tower_count)]
        for size in range(self.num_disks, 0, -1):
            self._create_disk(0, size)

    def _create_disk(self, tower_index, size):
        """Render a disk of given size on specified tower."""
        x_center = tower_index * self.tower_spacing + self.tower_spacing // 2
        stack_height = len(self.towers[tower_index])
        y = self.canvas_height - (stack_height + 1) * self.disk_height
        # Linear width interpolation
        min_w = int(self.tower_spacing * 0.2)
        max_w = int(self.tower_spacing * 0.9)
        denom = self.num_disks - 1 or 1
        width = min_w + (max_w - min_w) * (size - 1) // denom
        left, right = x_center - width//2, x_center + width//2
        cid = self.canvas.create_rectangle(left, y, right, y + self.disk_height,
                                           fill="skyblue", tags=("disk",))
        self.towers[tower_index].append((cid, size))

    def on_ButtonPress_1(self, event):
        """Pick up the top disk of its tower."""
        item = self.canvas.find_withtag("current")[0]
        for idx, tower in enumerate(self.towers):
            if tower and tower[-1][0] == item:
                self.drag_data.update({"item": item, "from_tower": idx,
                                       "x": event.x, "y": event.y})
                break

    def on_B1_Motion(self, event):
        """Drag: move selected disk with cursor."""
        item = self.drag_data["item"]
        if item:
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            self.canvas.move(item, dx, dy)
            self.drag_data.update({"x": event.x, "y": event.y})

    def on_ButtonRelease_1(self, event):
        """Release: validate move, snap disk, check win."""
        data = self.drag_data
        if not data["item"]:
            return
        src = data["from_tower"]
        drop = min(event.x // self.tower_spacing, self.tower_count-1)
        _, size = next(f for f in self.towers[src] if f[0] == data["item"])
        top = self.towers[drop][-1][1] if self.towers[drop] else None
        if top and size > top:
            self._draw_towers(); self._repaint_all()
        else:
            self.towers[src].pop()
            self.canvas.delete(data["item"])
            self._create_disk(drop, size)
            # Win if all disks moved to any non-source tower
            if any(len(t) == self.num_disks for t in self.towers[1:]):
                again = messagebox.askyesno("You win!", "Solved! Play again?")
                self.root.destroy()
                if again: TowerOfHanoiGame()
                return
        self.drag_data = {"item": None, "x": 0, "y": 0, "from_tower": None}

    def _repaint_all(self):
        """Repaint every disk from model state."""
        self.canvas.delete("disk")
        for i, tower in enumerate(self.towers):
            for (_cid, size) in tower:
                self._create_disk(i, size)

    def simulation(self):
        """Animate the minimal-move solution using a memory-efficient generator."""
        self.move_gen = self._solve_gen(self.num_disks, 0, 1, 2)
        self._start_simulation()

    def _solve_gen(self, n, src, aux, tgt):
        """Yield moves recursively: (src→tgt) pairs."""
        if n:
            yield from self._solve_gen(n-1, src, tgt, aux)
            yield (src, tgt)
            yield from self._solve_gen(n-1, aux, src, tgt)

    def _start_simulation(self):
        self._draw_towers(); self._init_stacks()
        self._run_next_move()

    def _run_next_move(self):
        """Pull next move from generator, animate, then schedule itself."""
        try:
            src, tgt = next(self.move_gen)
        except StopIteration:
            messagebox.showinfo("Simulation", "Simulation complete.")
            return
        cid, size = self.towers[src].pop()
        self.canvas.delete(cid)
        self._create_disk(tgt, size)
        delay = max(10, 5000 // (2**min(self.num_disks, 10)))
        self.root.after(delay, self._run_next_move)

if __name__ == "__main__":
    TowerOfHanoiGame()

