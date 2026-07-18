# =============================================================================
# HUMAN BEHAVIOR SIMULATOR
# Simulates realistic human interactions (typing, mouse, scrolling)
# =============================================================================

import asyncio
import math
import random
from typing import Optional


class BehaviorSimulator:
    """Simulates realistic human behavior for browser automation."""

    def __init__(self, page):
        self.page = page

    async def human_typing(self, selector: str, text: str, typo_rate: float = 0.02):
        """
        Simulate human-like typing with occasional typos and pauses.

        Args:
            selector: CSS selector for the input field
            text: Text to type
            typo_rate: Probability of making a typo per character (0.02 = 2%)
        """
        element = await self.page.query_selector(selector)
        if not element:
            # Fallback: try to find by name or placeholder
            return False

        await element.click()
        await asyncio.sleep(random.uniform(0.1, 0.3))

        for char in text:
            # Random pause (5% chance)
            if random.random() < 0.05:
                await asyncio.sleep(random.uniform(0.3, 1.0))

            # Typo simulation
            if random.random() < typo_rate:
                # Type wrong character
                wrong_char = random.choice("abcdefghijklmnopqrstuvwxyz")
                await element.type(wrong_char, delay=random.uniform(30, 80))
                await asyncio.sleep(random.uniform(0.1, 0.3))

                # Press backspace
                await element.press("Backspace")
                await asyncio.sleep(random.uniform(0.05, 0.15))

            # Type correct character
            delay = random.uniform(30, 80)  # 30ms to 80ms per character
            await element.type(char, delay=delay)

        return True

    async def human_click(self, selector: str):
        """Simulate human-like click with pre-click movement."""
        element = await self.page.query_selector(selector)
        if not element:
            return False

        # Random delay before clicking
        await asyncio.sleep(random.uniform(0.5, 2.0))

        # Move mouse near element first
        try:
            box = await element.bounding_box()
            if box:
                # Move to a random point near the element
                target_x = box["x"] + random.uniform(0, box["width"])
                target_y = box["y"] + random.uniform(0, box["height"])
                await self.page.mouse.move(target_x, target_y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
        except Exception:
            pass

        await element.click()
        return True

    async def random_mouse_movement(self, num_points: int = None):
        """
        Simulate random mouse movements using Bezier curves.

        Args:
            num_points: Number of target points (3-8)
        """
        if num_points is None:
            num_points = random.randint(3, 8)

        viewport = self.page.viewport_size
        if not viewport:
            return

        width, height = viewport["width"], viewport["height"]
        current_x, current_y = random.uniform(0, width), random.uniform(0, height)

        for _ in range(num_points):
            # Generate target point within viewport
            target_x = random.uniform(50, width - 50)
            target_y = random.uniform(50, height - 50)

            # Generate control point for Bezier curve
            mid_x = (current_x + target_x) / 2
            mid_y = (current_y + target_y) / 2
            control_x = mid_x + random.uniform(-50, 50)
            control_y = mid_y + random.uniform(-50, 50)

            # Number of steps per curve
            steps = random.randint(10, 30)

            for i in range(steps + 1):
                t = i / steps
                # Quadratic Bezier curve
                x = (1 - t) ** 2 * current_x + 2 * (1 - t) * t * control_x + t ** 2 * target_x
                y = (1 - t) ** 2 * current_y + 2 * (1 - t) * t * control_y + t ** 2 * target_y

                await self.page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.01, 0.05))

            current_x, current_y = target_x, target_y
            await asyncio.sleep(random.uniform(0.1, 0.3))

    async def random_scrolling(self, num_scrolls: int = None):
        """
        Simulate realistic scrolling behavior.

        Args:
            num_scrolls: Number of scroll actions (3-8)
        """
        if num_scrolls is None:
            num_scrolls = random.randint(3, 8)

        for _ in range(num_scrolls):
            scroll_amount = random.randint(100, 400)
            await self.page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(0.5, 2.0))

            # 30% chance to scroll back up a bit
            if random.random() < 0.3:
                up_amount = random.randint(50, 150)
                await self.page.evaluate(f"window.scrollBy(0, -{up_amount})")
                await asyncio.sleep(random.uniform(0.3, 0.8))

    async def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 5.0):
        """Add a random delay between actions."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    async def simulate_form_interaction(self, field_sequence: list):
        """
        Simulate human-like form interaction sequence.

        Args:
            field_sequence: List of dicts with 'selector' and 'value' keys
        """
        # Initial mouse movement
        await self.random_mouse_movement(num_points=random.randint(2, 4))

        for i, field in enumerate(field_sequence):
            # Scroll to field if needed
            element = await self.page.query_selector(field["selector"])
            if element:
                await element.scroll_into_view_if_needed()
                await asyncio.sleep(random.uniform(0.3, 0.8))

            # Fill the field
            if field.get("is_click"):
                await self.human_click(field["selector"])
            else:
                await self.human_typing(
                    field["selector"],
                    field["value"],
                    typo_rate=field.get("typo_rate", 0.02)
                )

            # Delay between fields
            if i < len(field_sequence) - 1:
                await asyncio.sleep(random.uniform(0.5, 1.5))

        # Random delay before submit
        await asyncio.sleep(random.uniform(1.0, 3.0))

    async def simulate_page_reading(self):
        """Simulate a user reading the page before interacting."""
        # Initial scroll to see page
        await self.random_scrolling(num_scrolls=random.randint(2, 4))
        await asyncio.sleep(random.uniform(1.0, 3.0))

        # Move mouse around
        await self.random_mouse_movement(num_points=random.randint(3, 6))
