from django import template

register = template.Library()

@register.filter
def range_filter(value):
    """Generate a range from 0 to value-1"""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)

@register.filter  
def sub(value, arg):
    """Subtract arg from value"""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter  
def add(value, arg):
    """Add arg to value"""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def get_letter(value, index):
    """Get letter at index from string"""
    try:
        return value[int(index)]
    except (IndexError, ValueError, TypeError):
        return ""

@register.filter
def is_star_point(board_size, position):
    """Check if position (row,col as 'row,col') is a star point"""
    try:
        board_size = int(board_size)
        row, col = map(int, position.split(','))
        
        # Star points for different board sizes
        if board_size == 9:
            star_points = [(2,2), (2,6), (4,4), (6,2), (6,6)]
        elif board_size == 13:
            star_points = [(3,3), (3,9), (6,6), (9,3), (9,9)]
        elif board_size == 15:
            star_points = [(3,3), (3,11), (7,7), (11,3), (11,11)]
        elif board_size == 19:
            star_points = [(3,3), (3,9), (3,15), (9,3), (9,9), (9,15), (15,3), (15,9), (15,15)]
        else:
            # For other sizes, use center and quarter points
            center = board_size // 2
            quarter = board_size // 4
            three_quarter = 3 * board_size // 4
            star_points = [(quarter, quarter), (quarter, three_quarter), (center, center), (three_quarter, quarter), (three_quarter, three_quarter)]
        
        return (row, col) in star_points
    except (ValueError, AttributeError):
        return False

@register.filter
def move_coordinate(move):
    """Convert a GameMove to coordinate notation (e.g., 'E7')"""
    try:
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        col_letter = letters[int(move.col)]
        row_number = int(move.row) + 1  # Convert 0-based to 1-based
        return f"{col_letter}{row_number}"
    except (IndexError, ValueError, AttributeError):
        return f"?{move.move_number}"