#!/usr/bin/env bash
set -u
BASE="$HOME/Scan"
PHOTO_DIR="$BASE/Photo"
RAW_DIR="$BASE/Raw"
LOCK_FILE="$BASE/.scan.lock"
SCANNER='pixma:04A91913_5E2C64'
mkdir -p "$PHOTO_DIR" "$RAW_DIR"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then echo "ERROR: another scan is already running."; exit 1; fi
next_number() {
    local dir="$1" ext="$2" file name num max=0
    shopt -s nullglob
    for file in "$dir"/*."$ext"; do
        name="$(basename "$file")"; num="${name%.$ext}"
        if [[ "$num" =~ ^[0-9]{6}$ ]]; then
            num=$((10#$num)); (( num > max )) && max=$num
        fi
    done
    printf "%06d" $((max + 1))
}
RAW_NUM="$(next_number "$RAW_DIR" tiff)"
PHOTO_NUM="$(next_number "$PHOTO_DIR" jpg)"
RAW_FILE="$RAW_DIR/$RAW_NUM.tiff"
echo
echo "=========================================="
echo "        PHOTO SCANNER"
echo "=========================================="
echo
echo "Scanner:        $SCANNER"
echo "Raw scan:       $RAW_FILE"
echo "First photo:    $PHOTO_NUM.jpg"
echo
echo "Place up to 4 photos on the scanner."
echo "Starting scan..."
echo
if ! scanimage -L 2>/dev/null | grep -Fq "$SCANNER"; then
    echo "ERROR: Canon scanner was not detected."
    echo
    scanimage -L 2>/dev/null || true
    exit 1
fi
if ! scanimage -d "$SCANNER" --resolution 1200 --format=tiff -o "$RAW_FILE"; then
    echo; echo "ERROR: scanner failed."; rm -f "$RAW_FILE"; exit 1
fi
if [[ ! -s "$RAW_FILE" ]]; then
    echo; echo "ERROR: scanner produced an empty TIFF."; rm -f "$RAW_FILE"; exit 1
fi
echo; echo "Scan complete."; echo "Raw TIFF kept at:"; echo "  $RAW_FILE"; echo; echo "Detecting photographs..."
PHOTO_DIR="$PHOTO_DIR" RAW_FILE="$RAW_FILE" PHOTO_NUM="$PHOTO_NUM" python3 <<'PY'
import os, sys, cv2, numpy as np
raw_file=os.environ['RAW_FILE']; photo_dir=os.environ['PHOTO_DIR']; photo_num=int(os.environ['PHOTO_NUM'])
MAX_PHOTOS=4; DARK_THRESHOLD=215; MAX_WORK_WIDTH=2400
try:
    image=cv2.imread(raw_file,cv2.IMREAD_COLOR)
    if image is None: raise RuntimeError('OpenCV could not read the TIFF.')
    original_h,original_w=image.shape[:2]
    scale=min(1.0,MAX_WORK_WIDTH/float(original_w))
    work=cv2.resize(image,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA) if scale<1 else image.copy()
    gray=cv2.cvtColor(work,cv2.COLOR_BGR2GRAY)
    mask=cv2.threshold(gray,DARK_THRESHOLD,255,cv2.THRESH_BINARY_INV)[1]
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_RECT,(25,25)))
    mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(5,5)))
    contours,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    image_area=work.shape[0]*work.shape[1]; candidates=[]
    for contour in contours:
        area=cv2.contourArea(contour)
        if area < image_area*0.015: continue
        rect=cv2.minAreaRect(contour); (cx,cy),(rw,rh),angle=rect
        if rw<=1 or rh<=1: continue
        rect_area=rw*rh; fill=area/rect_area
        if fill<0.45: continue
        aspect=max(rw,rh)/min(rw,rh)
        if aspect>3.5: continue
        box=np.array(cv2.boxPoints(rect),dtype=np.float32)
        x_min,x_max=float(np.min(box[:,0])),float(np.max(box[:,0])); y_min,y_max=float(np.min(box[:,1])),float(np.max(box[:,1]))
        border=max(8,int(min(work.shape[:2])*0.01))
        if x_min<=border or y_min<=border or x_max>=work.shape[1]-border or y_max>=work.shape[0]-border: continue
        candidates.append({'contour':contour,'rect':rect,'area':area,'box':box})
    candidates.sort(key=lambda c:c['area'],reverse=True); candidates=candidates[:MAX_PHOTOS]
    if not candidates: raise RuntimeError('No photographs were detected.')
    candidates.sort(key=lambda c:(cv2.minAreaRect(c['contour'])[0][1],cv2.minAreaRect(c['contour'])[0][0]))
    def order_points(pts):
        pts=np.array(pts,dtype=np.float32); s=pts.sum(axis=1); d=np.diff(pts,axis=1).reshape(-1)
        return np.array([pts[np.argmin(s)],pts[np.argmin(d)],pts[np.argmax(s)],pts[np.argmax(d)]],dtype=np.float32)
    cropped=[]
    for c in candidates:
        box=c['box']/scale if scale!=1 else c['box']; box=order_points(box); tl,tr,br,bl=box
        width=max(1,int(round(max(np.linalg.norm(br-bl),np.linalg.norm(tr-tl))))); height=max(1,int(round(max(np.linalg.norm(tr-br),np.linalg.norm(tl-bl)))))
        dst=np.array([[0,0],[width-1,0],[width-1,height-1],[0,height-1]],dtype=np.float32)
        crop=cv2.warpPerspective(image,cv2.getPerspectiveTransform(box,dst),(width,height),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
        if crop is None or crop.size==0: raise RuntimeError('Failed to crop one of the detected photographs.')
        cropped.append(crop)
    for i,crop in enumerate(cropped):
        output=os.path.join(photo_dir,f'{photo_num+i:06d}.jpg')
        if not cv2.imwrite(output,crop,[cv2.IMWRITE_JPEG_QUALITY,95]): raise RuntimeError(f'Failed to write {output}')
        print(f'Created: {output}')
    print(); print(f'Detected {len(cropped)} photograph(s).')
except Exception as exc:
    print(); print(f'ERROR: {exc}'); sys.exit(1)
PY
RESULT=$?
echo
if [[ "$RESULT" -ne 0 ]]; then echo "The raw TIFF has been kept:"; echo "  $RAW_FILE"; echo; echo "The JPGs were not considered reliable."; exit 1; fi
echo "=========================================="; echo "Scan completed successfully."; echo "=========================================="; echo; echo "Raw TIFF:"; echo "  $RAW_FILE"; echo; echo "Photos created:"; ls -1 "$PHOTO_DIR"/*.jpg 2>/dev/null | tail -n 2 || true
