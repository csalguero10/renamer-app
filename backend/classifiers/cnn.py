import os
CATEGORIES = [
    "cover",
    "back cover",
    "endpapers",
    "flyleaves",
    "frontispiece",
    "text",
    "illustration",
    "insert",
    "blank page",
    "reference"
]

def predict_with_cnn(pil_image):
    """Optional CNN inference. If model not found or torch not available, returns None."""
    try:
        import torch
        from torchvision import transforms
        model_path = os.path.join(os.path.dirname(__file__), "model.pth")
        if not os.path.exists(model_path):
            return None
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = torch.load(model_path, map_location=device)
        model.eval()
        t = transforms.Compose([
            transforms.Resize((224,224)),
            transforms.ToTensor(),
        ])
        x = t(pil_image).unsqueeze(0).to(device)
        with torch.no_grad():
            logits = model(x)
            pred = int(torch.argmax(logits, dim=1).cpu())
        if 0 <= pred < len(CATEGORIES):
            return CATEGORIES[pred]
        return None
    except Exception:
        return None
