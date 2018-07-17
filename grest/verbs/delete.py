#
# Copyright (C) 2018 Mostafa Moradian <mostafamoradian0@gmail.com>
#
# This file is part of grest.
#
# grest is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# grest is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with grest.  If not, see <http://www.gnu.org/licenses/>.
#

from __future__ import absolute_import

try:
    # For Python 3.0 and later
    from urllib.request import unquote
except ImportError:
    # Fall back to Python 2's urllib2
    from urllib2 import unquote

from neomodel import db
from neomodel.exception import DoesNotExist, RequiredProperty, UniqueProperty

import grest.messages as msg
from grest.exceptions import HTTPException
from grest.utils import serialize
from grest.validation import validate_models


def delete(self,
           request,
           primary_id,
           secondary_model_name=None,
           secondary_id=None):
    try:
        # patch __log
        self.__log = self._GRest__log

        (primary, secondary) = validate_models(self,
                                               primary_id,
                                               secondary_model_name,
                                               secondary_id)

        primary_selected_item = None
        if primary.id is not None:
            primary_selected_item = primary.model.nodes.get_or_none(
                **{primary.selection_field: primary.id})

        secondary_selected_item = None
        if secondary.id is not None:
            secondary_selected_item = secondary.model.nodes.get_or_none(
                **{secondary.selection_field: secondary.id})

        if all([primary_selected_item,
                secondary_selected_item,
                secondary.model,
                secondary.id]):
            # user either wants to update a relation or
            # has provided invalid information
            if hasattr(primary_selected_item, secondary.model_name):
                relation_exists = primary_selected_item.relation_exists(
                    secondary.model_name,
                    secondary_selected_item)
                if not relation_exists:
                    # There is an no relation
                    raise HTTPException(msg.RELATION_DOES_NOT_EXIST, 404)
                else:
                    # Get relation between primary and secondary objects
                    relation = getattr(
                        primary_selected_item,
                        secondary.model_name)

                    with db.transaction:
                        # remove all relationships
                        for each_relation in relation.all():
                            relation.disconnect(each_relation)

                        if secondary_selected_item not in relation.all():
                            return serialize(dict(result="OK"))
                        else:
                            raise HTTPException(msg.DELETE_FAILED,
                                                500)
        elif all([primary_selected_item is not None,
                  secondary.model is None,
                  secondary.id is None]):
            with db.transaction:
                if primary_selected_item.delete():
                    return serialize(dict(result="OK"))
                else:
                    raise HTTPException(msg.DELETE_FAILED, 500)
        else:
            raise HTTPException(msg.RELATION_DOES_NOT_EXIST, 404)
    except (DoesNotExist, AttributeError) as e:
        self.__log.exception(e)
        raise HTTPException(msg.ITEM_DOES_NOT_EXIST, 404)
    except UniqueProperty as e:
        self.__log.exception(e)
        raise HTTPException(msg.NON_UNIQUE_PROPERTIY, 409)
    except RequiredProperty as e:
        self.__log.exception(e)
        raise HTTPException(msg.REQUIRE_PROPERTY_MISSING, 500)