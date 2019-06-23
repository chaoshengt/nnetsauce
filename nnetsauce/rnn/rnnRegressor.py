u"""RNN Regressor"""

# Authors: Thierry Moudiki
#
# License: BSD 3

import numpy as np
import sklearn.metrics as skm2
from .rnn import RNN
from sklearn.base import RegressorMixin


class RNNRegressor(RNN, RegressorMixin):
    """RNN Regression model class derived from class RNN
    
       Parameters
       ----------
       obj: object
           any object containing a method fit (obj.fit()) and a method predict 
           (obj.predict())
       alpha: float
           smoothing parameter
       n_hidden_features: int
           number of nodes in the hidden layer
       activation_name: str
           activation function: 'relu', 'tanh', 'sigmoid', 'prelu' or 'elu'
       a: float
           hyperparameter for 'prelu' or 'elu' activation function
       nodes_sim: str
           type of simulation for the nodes: 'sobol', 'hammersley', 'halton', 
           'uniform'
       bias: boolean
           indicates if the hidden layer contains a bias term (True) or not 
           (False)
       dropout: float
           regularization parameter; (random) percentage of nodes dropped out 
           of the training
       direct_link: boolean
           indicates if the original predictors are included (True) in model's 
           fitting or not (False)
       n_clusters: int
           number of clusters for 'kmeans' or 'gmm' clustering (could be 0: 
               no clustering)
       type_clust: str
           type of clustering method: currently k-means ('kmeans') or Gaussian 
           Mixture Model ('gmm')
       type_scaling: a tuple of 3 strings
           scaling methods for inputs, hidden layer, and clustering respectively
           (and when relevant). 
           Currently available: standardization ('std') or MinMax scaling ('minmax')
       col_sample: float
           percentage of covariates randomly chosen for training  
       row_sample: float
           percentage of rows chosen for training, by stratified bootstrapping    
       seed: int 
           reproducibility seed for nodes_sim=='uniform'
       type_fit: str
           'regression'
    """

    # construct the object -----

    def __init__(
        self,
        obj,
        alpha=0.5,
        n_hidden_features=5,
        activation_name="relu",
        a=0.01,
        nodes_sim="sobol",
        bias=True,
        dropout=0,
        direct_link=True,
        n_clusters=2,
        type_clust="kmeans",
        type_scaling=("std", "std", "std"),
        col_sample=1, # probably don't want to subsample here
        row_sample=1, # probably don't want to subsample here
        seed=123,
    ):

        super().__init__(
            obj=obj,
            alpha=alpha,
            n_hidden_features=n_hidden_features,
            activation_name=activation_name,
            a=a,
            nodes_sim=nodes_sim,
            bias=bias,
            dropout=dropout,
            direct_link=direct_link,
            n_clusters=n_clusters,
            type_clust=type_clust,
            type_scaling=type_scaling,
            col_sample=col_sample,
            row_sample=row_sample,
            seed=seed,
        )

        self.type_fit = "regression"
     
        
    # one step, on one input     
    def fit_step(self, X, y, **kwargs):
        """Fit RNN model to training data (X, y).
        
        Parameters
        ----------
        X: {array-like}, shape = [n_samples, n_features]
            Training vectors, where n_samples is the number 
            of samples and n_features is the number of features.
        
        y: array-like, shape = [n_samples]
               Target values.
    
        **kwargs: additional parameters to be passed to 
                  self.cook_training_set or self.obj.fit
               
        Returns
        -------
        self: object
        """
        if (len(X.shape) == 1):
            X = X.reshape(-1, 1)
        
        # calls 'create_layer' from parent RNN: obtains centered_y, updates state H.
        # 'scaled_Z' is not used, but H
        centered_y, scaled_Z = self.cook_training_set(
            y=y, X=X, **kwargs
        )
        
        self.obj.fit(X = scaled_Z, y = centered_y, **kwargs)

        return self
    

    # one step, on one input 
    def predict_step(self, X, **kwargs):
        """Predict test data X.
        
        Parameters
        ----------
        X: {array-like}, shape = [n_samples, n_features]
            Training vectors, where n_samples is the number 
            of samples and n_features is the number of features.
        
        **kwargs: additional parameters to be passed to 
                  self.cook_test_set
               
        Returns
        -------
        model predictions: {array-like}
        """

        if len(X.shape) == 1:            
            X = X.reshape(-1, 1)            

        return self.y_mean + self.obj.predict(
                self.cook_test_set(X, **kwargs), **kwargs
            )
        


    def score_step(self, X, y, scoring=None, **kwargs):
        """ Score the model on test set covariates X and response y. """

        preds = self.predict_step(X)

        if (
            type(preds) == tuple
        ):  # if there are std. devs in the predictions
            preds = preds[0]

        if scoring is None:
            scoring = "neg_mean_squared_error"

        # check inputs
        assert scoring in (
            "explained_variance",
            "neg_mean_absolute_error",
            "neg_mean_squared_error",
            "neg_mean_squared_log_error",
            "neg_median_absolute_error",
            "r2",
        ), "'scoring' should be in ('explained_variance', 'neg_mean_absolute_error', \
                           'neg_mean_squared_error', 'neg_mean_squared_log_error', \
                           'neg_median_absolute_error', 'r2')"

        scoring_options = {
            "explained_variance": skm2.explained_variance_score,
            "neg_mean_absolute_error": skm2.mean_absolute_error,
            "neg_mean_squared_error": skm2.mean_squared_error,
            "neg_mean_squared_log_error": skm2.mean_squared_log_error,
            "neg_median_absolute_error": skm2.median_absolute_error,
            "r2": skm2.r2_score,
        }

        return scoring_options[scoring](y, preds, **kwargs)

    
    
    def fit(self, inputs, targets = None, scoring = None, n_params = None): 
        """ Train the model on multiple steps. """

        steps = inputs.shape[0]
    
        assert (steps > 0), "inputs.shape[0] must be > 0"
                
        assert (steps == targets.shape[0]), \
        "'inputs' and 'targets' must contain the same number of steps"
        
        self.steps = steps
        
        self.last_target = targets[-1, :] 
        
        loss = 0
        
        # for long sequences, add progress bar
        # for long sequences, add progress bar
        # for long sequences, add progress bar
        if scoring is None:    
        
            if targets is not None: 
            
                for i in range(steps):
                    self.fit_step(X = inputs[i,:], y = targets[i,:])
                    # compute AICc here instead
                    loss += self.score_step(X = inputs[i,:], y = targets[i,:])
                
                return loss/steps # return AICc
            
            else:
            
                for i in range(steps - 1):
                    self.fit_step(X = inputs[i,:], y = inputs[(i + 1), :])
                    # compute AICc here instead
                    loss += self.score_step(X = inputs[i,:], y = inputs[(i + 1), :])
                
                return loss/(steps - 1) # return AICc
        
        else: # scoring is not none 
            
            if targets is not None: 
            
                for i in range(steps):
                    self.fit_step(X = inputs[i,:], y = targets[i,:])
                    loss += self.score_step(X = inputs[i,:], y = targets[i,:], 
                                            scoring = scoring)
                
                return loss/steps
            
            else:
                
                for i in range(steps - 1):
                    self.fit_step(X = inputs[i,:], y = inputs[(i + 1), :])
                    # compute AICc here instead
                    loss += self.score_step(X = inputs[i,:], y = inputs[(i + 1), :], 
                                            scoring = scoring)
                
                return loss/(steps - 1) # return AICc 



    def predict(
        self, h=5, level=95, new_xreg=None, **kwargs
        ):
        
        assert (self.steps > 0), "method 'fit' must be called first"
        
        n_series = len(self.last_target)
        
        res = np.zeros((h, n_series))
        
        preds = self.predict_step(X = self.last_target)
        
        res[0, :] = preds
        
        for i in range(1, h):            
            preds = self.predict_step(X = preds)            
            res[i, ] = preds
        
        return res