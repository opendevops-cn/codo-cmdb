"""
Version : 0.0.1
Contact : 191715030@qq.com
Author  : shenshuo
Date    : 2023/2/15 14:59
Desc    : test
"""

from pydantic import BaseModel, Field


def test1():
    class BaseResponse(BaseModel):
        cloud_name: str = Field(..., description="云名称")
        account_id: str = Field(..., description="账号ID")
        instance_id: str = Field(..., description="实例ID")
        region: str = Field(..., description="地域")
        zone: str = Field(..., description="可用区")
        is_expired: int = Field(..., description="是否过期")

    base = BaseResponse(
        cloud_name="cloud_name",
        account_id="account_id",
        instance_id="instance_id",
        region="region",
        zone="zone",
        # is_expired=1
    )
    print(base.dict())


def test2():
    from pydantic import BaseModel

    class Person(BaseModel):
        name: str
        age: int

    person_data = {
        "name": "Alice",
        "age": 30
    }

    # 创建 Person 实例并验证数据
    person = Person(**person_data)
    print("Person", person)
    print(person.dict())

    # 在验证时引发错误
    invalid_person_data = {
        "name": "Bob",
        "age": "thirty"
    }
    invalid_person = Person(**invalid_person_data)
    print("invalid_person", invalid_person)


if __name__ == '__main__':
    test2()
