import pandas as pd
import os
import torch
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image

class EfficientNetEmbedding(torch.nn.Module):
    def __init__(self, model_name='efficientnetv2_s', embedding_dim=128):
        super().__init__()

        # Load the model without the weights and without the last layer
        self.backbone = timm.create_model(model_name, pretrained=False, num_classes=0)

        # We modify the first layer to accept our grayscale images
        first_conv = self.backbone.conv_stem
        self.backbone.conv_stem = torch.nn.Conv2d(
            in_channels=1,
            out_channels=first_conv.out_channels,
            kernel_size=first_conv.kernel_size,
            stride=first_conv.stride,
            padding=first_conv.padding,
            bias=first_conv.bias is not None
        )

        # Embedding layer
        self.embedding = torch.nn.Linear(self.backbone.num_features, embedding_dim)

    def forward(self, x):
        x = self.backbone(x)
        x = F.normalize(self.embedding(x), p=2, dim=1)  # L2 Normalization
        return x

def get_kanji_dataframe(df_path):
    """
    This function return the list of Kanji to be guessed based on those we learned
    during this semester, cleaned of the kanas and ～ symbol.
    """
    df = pd.read_csv(df_path)
    kana_string = "あアいイうウえエおオかカきキくクけケこコさサしシすスせセそソたタちチつツてテとトなナにニぬヌねネのノはハひヒふフへヘほホまマみミむムめメもモやヤゆユよヨらラりリるルれレろロわワをヲんンがガぎギぐグげゲごゴざザじジずズぜゼぞゾだダぢヂづヅでデどドばバびビぶブべベぼボぱパぴピぷプぺペぽポきゃキャきゅキュきょキョしゃシャしゅシュしょショちゃチャちゅチュちょチョにゃニャにゅニュにょニョひゃヒャひゅヒュひょヒョみゃミャみゅミュみょミョりゃリャりゅリュりょリョぎゃギャぎゅギュぎょギョじゃジャじゅジュじょジョびゃビャびゅビュびょビョぴゃピャぴゅピュぴょピョ"
    for j in range(len(df["Kanji"])):
        df.loc[j, "Kanji"] = "".join([i for i in df["Kanji"][j] if not(i in kana_string)])
    

    for j in range(len(df["Kanji"])):
        if (len(df["Kanji"][j]) > 1):
            for i in range(len(df["Kanji"][j])-1):
                df.loc[len(df["Kanji"]), ["Kanji", "Furigana"]] = (df.loc[j, "Kanji"][i+1], df.loc[j, "Furigana"])
            df.loc[j, "Kanji"] = df.loc[j, "Kanji"][0]

    # Clean the ～ char
    rows_to_drop = []
    for j in range(len(df["Kanji"])):
        if (df.loc[j, "Kanji"] == '～'):
            rows_to_drop.append(j)
            
    df = df.drop(rows_to_drop)
    df = df.reset_index(drop=True)

    return df

def load_model(model_path, device):
    """
    This function return a loaded net from a .pth file
    """
    return torch.load(model_path, map_location=device, weights_only=False)

# ---------------------------------Tools------------------------------------
def load_image(path, transform, device):
    """
    Load an image and automatically apply the given transform
    """
    img = Image.open(path)
    
    if img.mode == 'RGBA': # In case of images with a transparent background
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(background, img).convert("L")
    else:
        img = img.convert("L")

    tensor = transform(img).unsqueeze(0).to(device)
    return tensor

def get_embedding(net, image_tensor):
    """
    Return the embedding of a tensor
    """
    net.eval()
    with torch.no_grad():
        embedding = net(image_tensor)
    return embedding

def cosine_sim(embedding, reference_vectors):
    """
    Return the cosine similarities of the embedding for each reference vector
    """
    embedding = F.normalize(embedding, p=2, dim=1)
    reference_vectors = F.normalize(reference_vectors, p=2, dim=1)

    sims = torch.mm(embedding, reference_vectors.T)
    return sims.squeeze(0)

def get_reference_vectors(net, device, reference_dir, reference_transform):
    """
    Create the reference vectors and return them with their labels
    """
    labels = []
    reference_vectors = []

    for filename in os.listdir(reference_dir):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            label = os.path.splitext(filename)[0]
            labels.append(label)

            path = os.path.join(reference_dir, filename)
            image_tensor = load_image(path, reference_transform, device)
            embedding = get_embedding(net, image_tensor)
            reference_vectors.append(embedding)

    reference_vectors = torch.cat(reference_vectors, dim=0)
    return labels, reference_vectors

def get_N_first_labels(embedding, labels, reference_vectors, N = 5):
    """
    Return the N first labels, in descending order
    """
    similarities = cosine_sim(embedding, reference_vectors)
    
    top_args = torch.argsort(similarities, descending=True)
    
    return [labels[top_args[i]] for i in range(N)]
#---------------------------------------------------------------------------