"""
This module includes the base Model class used throughout TorCHmm. It also
includes some very basic models for discrete and continuous emissions.
"""
import torch
from torch.distributions import Categorical
from torch.distributions.multivariate_normal import MultivariateNormal


class Model(object):
    """
    This is an unsupervised model base class. It specifies the methods that
    should be implemented.
    """

    def init_params_random(self):
        """
        Randomly sets the parameters of the model; used for model fitting.
        """
        raise NotImplementedError("init_params_random method not implemented")

    def sample(self, *args, **kargs):
        """
        Draws a sample from the model. This method might take additional
        arguments for specifying things like how many samples to draw.
        """
        raise NotImplementedError("sample method not implemented")

    def log_prob(self, X):
        """
        Computes the log likelihood of the data X given the model.
        """
        raise NotImplementedError("log_likelihood method not implemented")

    def fit(self, X, *args, **kargs):
        """
        Updates the model parameters to best fit the data X. This might accept
        additional arguments that govern how the model is updated.
        """
        raise NotImplementedError("fit method not implemented")

    def parameters(self):
        """
        Returns the models parameters, as a list of tensors. This is is so
        other models can optimize this model. For example, in the case of
        nested models.
        """
        raise NotImplementedError("parameters method not implemented")

    def set_parameters(self, params):
        """
        Used to set the value of a models parameters
        """
        raise NotImplementedError("set_parameters method not implemented")


class CategoricalModel(Model):

    def __init__(self, probs=None, logits=None):
        """
        Accepts a set of probabilites OR logits for the model, NOT both.
        """
        if probs is not None and logits is not None:
            raise ValueError("Both probs and logits provided; only one should"
                             " be used.")
        elif probs is not None:
            self.logits = probs.log()
        elif logits is not None:
            self.logits = logits
        else:
            raise ValueError("Neither probs or logits provided; one must be.")

    def init_params_random(self):
        self.logits = torch.rand_like(self.logits).softmax(0).log()

    def sample(self, sample_shape=None):
        """
        Draws n samples from this model.
        """
        if sample_shape is None:
            sample_shape = torch.tensor([1])
        return Categorical(logits=self.logits).sample(sample_shape)

    def log_prob(self, value):
        """
        Returns the loglikelihood of x given the current categorical
        distribution.
        """
        return Categorical(logits=self.logits).log_prob(value)

    def parameters(self):
        """
        Returns the model parameters for optimization.
        """
        yield self.logits

    def set_parameters(self, params):
        """
        Returns the model parameters for optimization.
        """
        self.logits = params[0]

    def fit(self, X):
        """
        Update the logit vector based on the observed counts.

        .. todo::
            Maybe could be modified with weights to support baum welch?
        """
        counts = X.bincount(minlength=self.logits.shape[0]).float()
        prob = counts / counts.sum()
        self.logits = prob.log()


class DiagNormalModel(Model):

    def __init__(self, means, covs):
        """
        Accepts a set of mean and cov for each dimension.

        Currently assumes all dimensions are independent.
        """
        if not isinstance(means, torch.Tensor):
            raise ValueError("Means must be a tensor.")
        if not isinstance(covs, torch.Tensor):
            raise ValueError("Covs must be a tensor.")
        if means.shape != covs.shape:
            raise ValueError("Means and covs must have same shape!")

        self.means = means
        self.covs = covs

    def init_params_random(self):
        self.means.normal_()
        self.covs.log_normal_()

    def sample(self, sample_shape=None):
        """
        Draws n samples from this model.
        """
        if sample_shape is None:
            sample_shape = torch.tensor([1])
        return MultivariateNormal(
            loc=self.means,
            covariance_matrix=self.covs.abs().diag()).sample(sample_shape)

    def log_prob(self, value):
        """
        Returns the loglikelihood of x given the current categorical
        distribution.
        """
        return MultivariateNormal(
            loc=self.means,
            covariance_matrix=self.covs.abs().diag()).log_prob(value)

    def parameters(self):
        """
        Returns the model parameters for optimization.
        """
        yield self.means
        yield self.covs

    def set_parameters(self, params):
        """
        Sets the model parameters.
        """
        print("SETTING", params)
        self.means = params[0]
        self.covs = params[1]

    def fit(self, X):
        """
        Update the logit vector based on the observed counts.

        .. todo::
            Maybe could be modified with weights to support baum welch?
        """
        self.means = X.mean(0)
        self.covs = X.std(0).pow(2)