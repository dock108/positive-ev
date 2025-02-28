from PIL import Image
import os

def round_corners(image, radius):
    """Round the corners of the image."""
    # Create a mask for rounded corners
    mask = Image.new('L', image.size, 0)
    
    # Create solid corners
    for i in range(radius):
        for j in range(radius):
            # Distance from corner
            distance = ((radius - i) ** 2 + (radius - j) ** 2) ** 0.5
            if distance <= radius:
                # Top left
                mask.putpixel((i, j), 255)
                # Top right
                mask.putpixel((image.width - i - 1, j), 255)
                # Bottom left
                mask.putpixel((i, image.height - j - 1), 255)
                # Bottom right
                mask.putpixel((image.width - i - 1, image.height - j - 1), 255)
    
    # Fill the middle
    for i in range(radius, image.width - radius):
        for j in range(image.height):
            mask.putpixel((i, j), 255)
    for i in range(image.width):
        for j in range(radius, image.height - radius):
            mask.putpixel((i, j), 255)
    
    output = Image.new('RGBA', image.size, (0, 0, 0, 0))
    output.paste(image, mask=mask)
    return output

def generate_icons(source_image_path, output_dir):
    """Generate all required icon sizes from source image."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Open source image
    img = Image.open(source_image_path)
    
    # Define required sizes
    sizes = {
        'favicon.png': 32,
        'icon-192.png': 192,
        'icon-512.png': 512,
        'maskable-icon.png': 512  # This one might need manual adjustment for maskable format
    }
    
    # Generate each size
    for filename, size in sizes.items():
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        rounded = round_corners(resized, size // 8)  # Radius is 1/8 of the size
        output_path = os.path.join(output_dir, filename)
        rounded.save(output_path, 'PNG')
        print(f"Generated {filename} ({size}x{size}px)")
    
    # Special handling for iOS icon
    ios_size = 180
    ios_img = img.resize((int(ios_size * 0.8), int(ios_size * 0.8)), Image.Resampling.LANCZOS)
    
    # Create a new image with black background
    ios_bg = Image.new('RGBA', (ios_size, ios_size), (0, 0, 0, 255))
    
    # Calculate position to center the logo
    paste_x = (ios_size - ios_img.width) // 2
    paste_y = (ios_size - ios_img.height) // 2
    
    # Convert to RGBA if not already
    if ios_img.mode != 'RGBA':
        ios_img = ios_img.convert('RGBA')
    
    # Paste the resized logo onto the background
    ios_bg.paste(ios_img, (paste_x, paste_y), ios_img.split()[3])  # Use alpha channel as mask
    
    # Round the corners of the iOS icon
    ios_rounded = round_corners(ios_bg, ios_size // 8)
    
    # Save the iOS icon
    ios_output = os.path.join(output_dir, 'apple-touch-icon.png')
    ios_rounded.save(ios_output, 'PNG')
    print("Generated apple-touch-icon.png ({}x{}px)".format(ios_size, ios_size))
    
    # Also save as logo.png for navbar
    logo_output = os.path.join(output_dir, 'logo.png')
    ios_rounded.resize((32, 32), Image.Resampling.LANCZOS).save(logo_output, 'PNG')
    print("Generated logo.png (32x32px)")

if __name__ == "__main__":
    # Get the absolute path to the script's directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set paths relative to script location
    source_image = os.path.join(script_dir, '..', 'static', 'images', 'logo-source.png')
    output_dir = os.path.join(script_dir, '..', 'static', 'images')
    
    generate_icons(source_image, output_dir) 