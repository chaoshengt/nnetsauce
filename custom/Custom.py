import numpy as np
from ..base import Base
from ..utils import matrixops as mo

class Custom(Base):
    """Custom sklearn (or else) model class derived from class Base
    
       Parameters
       ----------
       n_hidden_features: int
           number of nodes in the hidden layer
       activation_name: str
           activation function: 'relu', 'tanh' or 'sigmoid'
    """
    
    # construct the object -----
    
    def __init__(self, regr,
                 n_hidden_features=5, 
                 activation_name='relu',
                 nodes_sim='sobol',
                 n_clusters=2,
                 seed = 123):
                
        super().__init__(n_hidden_features, activation_name,
                         nodes_sim, n_clusters, seed)
        self.regr = regr

        
    def get_params(self):
        
        return super().get_params()

    
    def set_params(self, n_hidden_features=5, 
                   activation_name='relu', nodes_sim='sobol',
                   n_clusters=2, seed = 123):
        
        super().set_params(n_hidden_features=n_hidden_features, 
             activation_name=activation_name, nodes_sim=nodes_sim, 
             n_clusters=n_clusters, seed=seed)
 
    
    def fit(self, X, y, **kwargs):
        
        centered_y, scaled_Z = self.preproc_training_set(y = y, X = X)
        self.regr.fit(scaled_Z, centered_y, **kwargs)
        
        return self

    
    def predict(self, X, **kwargs):
        
        if len(X.shape) == 1:
            n_features = X.shape[0]
            new_X = mo.rbind(X.reshape(1, n_features), 
                             np.ones(n_features).reshape(1, n_features))        
            
            return (self.y_mean + self.regr.predict(self.preproc_test_set(new_X), 
                                               **kwargs))[0]
        else:
            return self.y_mean + self.regr.predict(self.preproc_test_set(X), 
                                               **kwargs)
        
        
