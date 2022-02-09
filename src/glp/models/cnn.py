import torch
from torch import nn

# A simple CNN model inspired by https://github.com/ML-Bioinfo-CEITEC/genomic_benchmarks/blob/main/src/genomic_benchmarks/models/torch.py
class CNN(nn.Module):
    def __init__(self, number_of_classes, vocab_size, embedding_dim, input_len):
        super(CNN, self).__init__()
        if number_of_classes == 2:
            number_of_output_neurons = 1
            loss = torch.nn.functional.binary_cross_entropy_with_logits
            output_activation = nn.Sigmoid()
        else:
            raise Exception("Not implemented for number_of_classes!=2")
            # number_of_output_neurons = number_of_classes
            # loss = torch.nn.CrossEntropyLoss()
            # output_activation = nn.Softmax(dim=)

        self.embeddings = nn.Embedding(vocab_size, embedding_dim)
        self.conv1 = nn.Conv1d(in_channels=embedding_dim, out_channels=16, kernel_size=8, bias=True)
        self.norm1 = nn.BatchNorm1d(16)
        self.relu = nn.ReLU()
        self.pool1 = nn.MaxPool1d(2)

        self.conv2 = nn.Conv1d(in_channels=16, out_channels=8, kernel_size=8, bias=True)
        self.norm2 = nn.BatchNorm1d(8)
        self.pool2 = nn.MaxPool1d(2)

        self.conv3 = nn.Conv1d(in_channels=8, out_channels=4, kernel_size=8, bias=True)
        self.norm3 = nn.BatchNorm1d(4)
        self.pool3 = nn.MaxPool1d(2)

        #         compute output shape of conv layers
        self.flatten = nn.Flatten()
        self.lin1 = nn.Linear(self.count_flatten_size(input_len), 512)
        self.lin2 = nn.Linear(512, number_of_output_neurons)
        self.output_activation = output_activation
        self.loss = loss

    def count_flatten_size(self, input_len):
        zeros = torch.zeros([1, input_len], dtype=torch.long)
        x = self.embeddings(zeros)
        x = x.transpose(1, 2)
        x = self.conv1(x)
        x = self.norm1(x)
        x = self.relu(x)
        x = self.pool1(x)

        x = self.conv2(x)
        x = self.norm2(x)
        x = self.relu(x)
        x = self.pool2(x)

        x = self.conv3(x)
        x = self.norm3(x)
        x = self.relu(x)
        x = self.pool3(x)

        x = self.flatten(x)
        return x.size()[1]

    def forward(self, x):
        x = self.embeddings(x)
        x = x.transpose(1, 2)
        x = self.conv1(x)
        x = self.norm1(x)
        x = self.relu(x)
        x = self.pool1(x)

        x = self.conv2(x)
        x = self.norm2(x)
        x = self.relu(x)
        x = self.pool2(x)

        x = self.conv3(x)
        x = self.norm3(x)
        x = self.relu(x)
        x = self.pool3(x)

        x = self.flatten(x)
        x = self.lin1(x)
        x = self.lin2(x)
        x = self.output_activation(x)
        return x

    def train_loop(self, dataloader, optimizer, val_dataloader):
        for x, y in dataloader:
            optimizer.zero_grad()
            pred = self(x)
            if y.shape != pred.shape:
                y = y.unsqueeze(1)
                y = y.float()
            loss = self.loss(pred, y)
            loss.backward()
            optimizer.step()


        train_loss, train_correct = self._eval(dataloader=dataloader)
        if val_dataloader != None:
            val_loss, val_correct = self._eval(dataloader=val_dataloader)
            print(f"Train metrics: \n Accuracy: {(100*train_correct):>0.1f}%, Avg loss: {train_loss:>8f} Val accuracy: {(100*val_correct):>0.1f}%, Val avg loss: {val_loss:>8f} \n")
        else:
            print(f"Train metrics: \n Accuracy: {(100*train_correct):>0.1f}%, Avg loss: {train_loss:>8f} \n")


    def train(self, dataloader, epochs, val_datdaloader = None):
        optimizer = torch.optim.Adam(self.parameters())
        for t in range(epochs):
            print(f"Epoch {t}")
            self.train_loop(dataloader, optimizer, val_datdaloader)

    def _eval(self, dataloader):
        size = dataloader.dataset.__len__()
        num_batches = len(dataloader)
        loss, correct = 0, 0

        with torch.no_grad():
            for X, y in dataloader:
                pred = self(X)
                if y.shape != pred.shape:
                    y = y.unsqueeze(1)
                    y = y.float()
                loss += self.loss(pred, y).item()
                correct += (torch.round(pred) == y).sum().item()

        loss /= num_batches
        correct /= size

        return loss, correct

# TODO: update for multiclass classification datasets
    def test(self, dataloader, positive_label = 1):
        size = dataloader.dataset.__len__()
        num_batches = len(dataloader)
        test_loss, correct = 0, 0
        tp, p, fp = 0, 0, 0

        with torch.no_grad():
            for X, y in dataloader:
                pred = self(X)
                if y.shape != pred.shape:
                    y = y.unsqueeze(1)
                    y = y.float()
                test_loss += self.loss(pred, y).item()
                correct += (torch.round(pred) == y).sum().item()
                p += (y == positive_label).sum().item() 
                if(positive_label == 1):
                    tp += (y * pred).sum(dim=0).item()
                    fp += ((1 - y) * pred).sum(dim=0).item()
                else:
                    tp += ((1 - y) * (1 - pred)).sum(dim=0).item()
                    fp += (y * (1 - pred)).sum(dim=0).item()

        print("p ", p, "; tp ", tp, "; fp ", fp)
        recall = tp / p
        precision = tp / (tp + fp)
        print("recall ", recall, "; precision ", precision)
        f1_score = 2 * precision * recall / (precision + recall)
        
        print("num_batches", num_batches)
        print("correct", correct)
        print("size", size)

        test_loss /= num_batches
        accuracy = correct / size
        print(f"Test metrics: \n Accuracy: {accuracy:>6f}, F1 score: {f1_score:>6f}, Avg loss: {test_loss:>6f} \n")
        
        return accuracy, f1_score