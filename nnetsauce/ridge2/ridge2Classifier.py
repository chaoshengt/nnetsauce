"""Ridge model for classification"""

# Authors: Thierry Moudiki
#
# License: BSD 3

import numpy as np
from scipy.optimize import minimize
import sklearn.metrics as skm2
from .ridge2 import Ridge2
from ..utils import matrixops as mo
from ..utils import misc as mx
from sklearn.base import ClassifierMixin
from scipy.special import logsumexp


class Ridge2Classifier(Ridge2, ClassifierMixin):
    """Ridge Classification model class with 2 regularization parameters derived from class Ridge
    
       Parameters
       ----------
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
       cluster_encode: bool
           defines how the variable containing clusters is treated (default is one-hot)
           if `False`, then labels are used, without one-hot encoding
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
       lambda1: float
           regularization parameter on direct link
       lambda2: float
           regularization parameter on hidden layer
       seed: int 
           reproducibility seed for nodes_sim=='uniform'
    """

    # construct the object -----

    def __init__(
        self,
        n_hidden_features=5,
        activation_name="relu",
        a=0.01,
        nodes_sim="sobol",
        bias=True,
        dropout=0,
        direct_link=True,
        n_clusters=2,
        cluster_encode=True,
        type_clust="kmeans",
        type_scaling=("std", "std", "std"),
        col_sample=1,
        row_sample=1,
        lambda1=0.1,
        lambda2=0.1,
        seed=123,
    ):

        super().__init__(
            n_hidden_features=n_hidden_features,
            activation_name=activation_name,
            a=a,
            nodes_sim=nodes_sim,
            bias=bias,
            dropout=dropout,
            direct_link=direct_link,
            n_clusters=n_clusters,
            cluster_encode=cluster_encode,
            type_clust=type_clust,
            type_scaling=type_scaling,
            col_sample=col_sample,
            row_sample=row_sample,
            lambda1=lambda1,
            lambda2=lambda2,
            seed=seed,
        )

        self.type_fit = "classification"

    def loglik(self, X, Y, **kwargs):
        """Log-likelihood for training data (X, Y).
        
        Parameters
        ----------
        X: {array-like}, shape = [n_samples, n_features]
            Training vectors, where n_samples is the number 
            of samples and n_features is the number of features.
        
        Y: array-like, shape = [n_samples]
               One-hot encode target values.
    
        **kwargs: additional parameters to be passed to 
                  self.cook_training_set or self.obj.fit
               
        Returns
        -------
        """

        def loglik_grad_hess(Y, X, B, XB, hessian=True, **kwargs):
            # nobs, n_classes
            n, K = Y.shape

            # total number of covariates
            p = X.shape[1]

            # initial number of covariates
            init_p = p - self.n_hidden_features

            max_double = 709.0
            XB[XB > max_double] = max_double
            exp_XB = np.exp(XB)
            probs = exp_XB / exp_XB.sum(axis=1)[:, None]

            # gradient -----
            # (Y - p) -> (n, K)
            # X -> (n, p)
            # (K, n) %*% (n, p) -> (K, p)
            if hessian is False:
                grad = -np.dot((Y - probs).T, X) / n
                grad += self.lambda1 * B[0:init_p, :].sum(axis=0)[:, None]
                grad += self.lambda2 * B[init_p:p, :].sum(axis=0)[:, None]

                return grad.flatten()

            # hessian -----
            if hessian is True:
                Kp = K * p
                hess = np.zeros((Kp, Kp), float)
                for k1 in range(K):
                    x_index = range(k1 * p, (k1 + 1) * p)
                    for k2 in range(k1, K):
                        y_index = range(k2 * p, (k2 + 1) * p)
                        H_sub = (
                            -np.dot(
                                X.T, (probs[:, k1] * probs[:, k2])[:, None] * X
                            )
                            / n
                        )  # do not store
                        hess[np.ix_(x_index, y_index)] = hess[
                            np.ix_(y_index, x_index)
                        ] = H_sub

                return hess + (self.lambda1 + self.lambda2) * np.identity(Kp)

        # total number of covariates
        p = X.shape[1]

        # initial number of covariates
        init_p = p - self.n_hidden_features

        # log-likelihood (1st return)
        def loglik_func(x):
            # (p, K)
            B = x.reshape(Y.shape[1], p).T

            # (n, K)
            XB = mo.safe_sparse_dot(X, B)

            res = -(np.sum(Y * XB, axis=1) - logsumexp(XB)).mean()

            res += 0.5 * self.lambda1 * mo.squared_norm(B[0:init_p, :])
            res += 0.5 * self.lambda2 * mo.squared_norm(B[init_p:p, :])

            return res

        # gradient of log-likelihood
        def grad_func(x):
            # (p, K)
            B = x.reshape(Y.shape[1], p).T

            return loglik_grad_hess(
                Y=Y,
                X=X,
                B=B,
                XB=mo.safe_sparse_dot(X, B),
                hessian=False,
                **kwargs
            )

        # hessian of log-likelihood
        def hessian_func(x):
            # (p, K)
            B = x.reshape(Y.shape[1], p).T

            return loglik_grad_hess(
                Y=Y,
                X=X,
                B=B,
                XB=mo.safe_sparse_dot(X, B),
                hessian=True,
                **kwargs
            )

        return loglik_func, grad_func, hessian_func

    # newton-cg
    # L-BFGS-B
    def fit(self, X, y, solver="L-BFGS-B", **kwargs):
        """Fit Ridge model to training data (X, y).
           for beta: regression coeffs (beta11, ..., beta1p, ..., betaK1, ..., betaKp)
           for K classes and p covariates.

        
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

        assert mx.is_factor(y), "y must contain only integers"

        output_y, scaled_Z = self.cook_training_set(y=y, X=X, **kwargs)

        self.n_classes = len(np.unique(y))

        Y = mo.one_hot_encode2(output_y, self.n_classes)

        # optimize for beta, minimize self.loglik (maximize loglik) -----
        loglik_func, grad_func, hessian_func = self.loglik(X=scaled_Z, Y=Y)

        if solver == "L-BFGS-B":
            self.beta = minimize(
                fun=loglik_func,
                x0=np.zeros(scaled_Z.shape[1] * self.n_classes),
                jac=grad_func,
                method=solver,
            ).x

        if solver in ("Newton-CG", "trust-ncg"):
            self.beta = minimize(
                fun=loglik_func,
                x0=np.zeros(scaled_Z.shape[1] * self.n_classes),
                jac=grad_func,
                hess=hessian_func,
                method=solver,
            ).x

        return self

    def predict(self, X, **kwargs):
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

        return np.argmax(self.predict_proba(X, **kwargs), axis=1)

    def predict_proba(self, X, **kwargs):
        """Predict probabilities for test data X.
        
        Parameters
        ----------
        X: {array-like}, shape = [n_samples, n_features]
            Training vectors, where n_samples is the number 
            of samples and n_features is the number of features.
        
        **kwargs: additional parameters to be passed to 
                  self.cook_test_set
               
        Returns
        -------
        probability estimates for test data: {array-like}        
        """
        if len(X.shape) == 1:

            n_features = X.shape[0]
            new_X = mo.rbind(
                X.reshape(1, n_features),
                np.ones(n_features).reshape(1, n_features),
            )

            Z = self.cook_test_set(new_X, **kwargs)

        else:

            Z = self.cook_test_set(X, **kwargs)

        ZB = mo.safe_sparse_dot(
            Z,
            self.beta.reshape(
                self.n_classes,
                X.shape[1] + self.n_hidden_features + self.n_clusters,
            ).T,
        )
        exp_ZB = np.exp(ZB)

        return exp_ZB / exp_ZB.sum(axis=1)[:, None]

    def score(self, X, y, scoring=None, **kwargs):
        """ Score the model on test set covariates X and response y. """

        preds = self.predict(X)

        if scoring is None:
            scoring = "accuracy"

        # check inputs
        assert scoring in (
            "accuracy",
            "average_precision",
            "brier_score_loss",
            "f1",
            "f1_micro",
            "f1_macro",
            "f1_weighted",
            "f1_samples",
            "neg_log_loss",
            "precision",
            "recall",
            "roc_auc",
        ), "'scoring' should be in ('accuracy', 'average_precision', \
                           'brier_score_loss', 'f1', 'f1_micro', \
                           'f1_macro', 'f1_weighted',  'f1_samples', \
                           'neg_log_loss', 'precision', 'recall', \
                           'roc_auc')"

        scoring_options = {
            "accuracy": skm2.accuracy_score,
            "average_precision": skm2.average_precision_score,
            "brier_score_loss": skm2.brier_score_loss,
            "f1": skm2.f1_score,
            "f1_micro": skm2.f1_score,
            "f1_macro": skm2.f1_score,
            "f1_weighted": skm2.f1_score,
            "f1_samples": skm2.f1_score,
            "neg_log_loss": skm2.log_loss,
            "precision": skm2.precision_score,
            "recall": skm2.recall_score,
            "roc_auc": skm2.roc_auc_score,
        }

        return scoring_options[scoring](y, preds, **kwargs)
