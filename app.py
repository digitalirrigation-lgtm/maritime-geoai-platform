def generate_satellite_image(lat, lon, mode='top_down', size=800):
    """
    Generate a realistic satellite image from 200m altitude.
    Uses NumPy for fast background and PIL for ship/overlay.
    """
    # Create a base ocean gradient using NumPy
    # We'll use vectorized operations for speed
    y = np.arange(size).reshape(size, 1)
    x = np.arange(size).reshape(1, size)
    
    # Depth gradient: darker at bottom (away from sun)
    factor = y / size
    r_base = 20 + 30 * (1 - factor)
    g_base = 60 + 60 * (1 - factor)
    b_base = 140 + 60 * (1 - factor)
    
    # Add wave patterns (sinusoidal)
    wave = 15 * np.sin(x/30 + y/20) + 10 * np.sin(x/50 - y/40)
    r = np.clip(r_base + wave, 0, 255).astype(np.uint8)
    g = np.clip(g_base + wave, 0, 255).astype(np.uint8)
    b = np.clip(b_base + wave, 0, 255).astype(np.uint8)
    
    # Combine into RGB image
    img_np = np.stack([r, g, b], axis=2)
    
    # Determine if near land (simplified based on lat/lon)
    near_land = False
    if -5 <= lon <= 35 and 30 <= lat <= 38:
        near_land = True
    elif -10 <= lon <= -5 and 35 <= lat <= 37:
        near_land = True
    elif -20 <= lon <= -10 and 35 <= lat <= 42:
        near_land = True
    
    if near_land:
        # Draw a coastline: land mass above a certain line
        coast_y = int(size * 0.7)  # coastline at 70% from top
        # Create land mask (above coast_y)
        land_mask = np.zeros((size, size), dtype=bool)
        for i in range(size):
            if i < coast_y:
                land_mask[i, :] = True
        # Assign land colors (green/brown) for pixels above coast
        land_color = np.array([80, 140, 60], dtype=np.uint8)
        # Add some variation
        for i in range(coast_y):
            for j in range(size):
                if np.random.random() > 0.3:  # random patches
                    variation = np.random.randint(-20, 20, 3)
                    img_np[i, j] = np.clip(land_color + variation, 0, 255)
        # Draw a sandy beach line at coast
        for j in range(size):
            img_np[coast_y, j] = [220, 200, 150]
        # Add wave foam near coast
        for j in range(size):
            y_wave = coast_y + int(10 * math.sin(j/20))
            if y_wave < size:
                img_np[y_wave, j] = [255, 255, 255]
    
    # Add sun glint (bright spot)
    glint_center = (int(size*0.7), int(size*0.2))
    for i in range(30):
        rad = 20 + i*8
        alpha = int(100 - i*3)
        if alpha > 0:
            # Draw a circle with transparency using PIL later, but we'll do it via numpy
            # We'll create a mask and apply a bright color with reduced opacity
            pass
    # We'll use PIL for glint because alpha is easier there.
    
    # Convert to PIL Image for easy drawing of ship, clouds, glint, and text
    img_pil = Image.fromarray(img_np)
    draw = ImageDraw.Draw(img_pil, 'RGBA')
    
    # Sun glint (semi-transparent circles)
    glint_center = (int(size*0.7), int(size*0.2))
    for i in range(20):
        rad = 20 + i*8
        alpha = int(80 - i*3)
        if alpha > 0:
            draw.ellipse((glint_center[0]-rad, glint_center[1]-rad,
                          glint_center[0]+rad, glint_center[1]+rad),
                         fill=(255, 255, 200, alpha))
    
    # Clouds (semi-transparent white clusters)
    for _ in range(10):
        cx = np.random.randint(0, size)
        cy = np.random.randint(0, int(size*0.5))
        r = np.random.randint(40, 100)
        for i in range(5):
            dx = np.random.randint(-r//2, r//2)
            dy = np.random.randint(-r//2, r//2)
            cr = r - 20 + np.random.randint(0, 30)
            alpha = np.random.randint(80, 180)
            draw.ellipse((cx+dx-cr, cy+dy-cr, cx+dx+cr, cy+dy+cr),
                         fill=(255, 255, 255, alpha))
    
    # Draw the ship (icon) at the center
    cx, cy = size//2, size//2
    # Hull (dark gray)
    draw.rectangle([cx-20, cy-10, cx+20, cy+10], fill=(60,60,80), outline=(200,200,200))
    # Superstructure (white)
    draw.rectangle([cx-10, cy-25, cx+10, cy-15], fill=(200,200,200), outline=(100,100,100))
    # Chimney (red)
    draw.rectangle([cx-5, cy-40, cx+5, cy-30], fill=(200,50,50))
    # Smoke (gray circles)
    for dx, dy in [(0,-45), (10,-50), (20,-55)]:
        draw.ellipse((cx+dx-8, cy+dy-8, cx+dx+8, cy+dy+8), fill=(180,180,180,150))
    # Wake (white lines)
    for i in range(3):
        x1 = cx - 30 - i*5
        y1 = cy - 5 + i*5
        x2 = cx - 60 - i*10
        y2 = cy - 15 + i*10
        draw.line([(x1,y1), (x2,y2)], fill=(255,255,255,150), width=3)
    
    # If voyage complete (progress >= 100), show "Destination Reached" overlay
    progress = st.session_state.live_progress
    if progress >= 99.9:
        # Draw a banner
        draw.rectangle([size//4, size//2-30, 3*size//4, size//2+30], fill=(0,255,0,180))
        draw.text((size//2, size//2), "🚢 DESTINATION REACHED!", fill=(0,0,0), anchor="mm", font=None)  # font will use default
    
    # Convert back to RGB (discard alpha)
    img_rgb = img_pil.convert('RGB')
    img_final = np.array(img_rgb)
    
    # Apply mode adjustments
    if mode == 'thermal':
        # Thermal: map to red/orange tones
        img_final = img_final.astype(np.float32)
        img_final[:, :, 0] = np.clip(img_final[:, :, 0] * 0.8 + 100, 0, 255)
        img_final[:, :, 1] = np.clip(img_final[:, :, 1] * 0.3, 0, 255)
        img_final[:, :, 2] = np.clip(img_final[:, :, 2] * 0.2, 0, 255)
        img_final = img_final.astype(np.uint8)
    elif mode == 'multispectral':
        # Enhance colors
        img_final = img_final.astype(np.float32)
        img_final[:, :, 0] = np.clip(img_final[:, :, 0] * 1.3, 0, 255)
        img_final[:, :, 1] = np.clip(img_final[:, :, 1] * 1.2, 0, 255)
        img_final[:, :, 2] = np.clip(img_final[:, :, 2] * 1.5, 0, 255)
        img_final = img_final.astype(np.uint8)
    
    return img_final
