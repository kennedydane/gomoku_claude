#!/usr/bin/env python3
"""Simple test to verify Dear PyGUI is working."""

import dearpygui.dearpygui as dpg

dpg.create_context()

with dpg.window(label="Gomoku Test", width=600, height=600):
    dpg.add_text("Gomoku Game Board Test")
    
    # Create a simple drawing for the board
    with dpg.drawlist(width=450, height=450):
        # Draw grid
        for i in range(16):
            # Vertical lines
            dpg.draw_line((i * 30, 0), (i * 30, 450), color=(100, 100, 100))
            # Horizontal lines
            dpg.draw_line((0, i * 30), (450, i * 30), color=(100, 100, 100))
        
        # Draw some test stones
        dpg.draw_circle((7*30, 7*30), 12, color=(20, 20, 20), fill=(20, 20, 20))  # Black stone
        dpg.draw_circle((7*30, 8*30), 12, color=(240, 240, 240), fill=(240, 240, 240))  # White stone
        dpg.draw_circle((8*30, 7*30), 12, color=(240, 240, 240), fill=(240, 240, 240))  # White stone
        dpg.draw_circle((8*30, 8*30), 12, color=(20, 20, 20), fill=(20, 20, 20))  # Black stone

dpg.create_viewport(title="Gomoku Test", width=650, height=650)
dpg.setup_dearpygui()
dpg.show_viewport()

# Start the Dear PyGUI render loop
while dpg.is_dearpygui_running():
    dpg.render_dearpygui_frame()

dpg.destroy_context()