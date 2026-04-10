from rest_framework import serializers


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class RegistrationSerializer(EmailSerializer):
    domainId = serializers.UUIDField(required=False)
    domainUuid = serializers.UUIDField(required=False)

    def validate(self, attrs):
        domain_id = attrs.get("domainId") or attrs.get("domainUuid")
        if domain_id is not None:
            attrs["domainId"] = domain_id
        attrs.pop("domainUuid", None)
        return attrs


class VerifyOtpSerializer(EmailSerializer):
    otp = serializers.RegexField(regex=r"^\d{6}$")


class RefreshSerializer(serializers.Serializer):
    refreshToken = serializers.CharField(min_length=32)


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8)


class DomainSelectSerializer(serializers.Serializer):
    domainId = serializers.UUIDField()


class AdminDomainCreateSerializer(serializers.Serializer):
    identifier = serializers.RegexField(regex=r"^[a-z0-9-]+$", min_length=2, max_length=50)
    label = serializers.CharField(min_length=2, max_length=100)
    extensionStart = serializers.IntegerField(min_value=100, max_value=999999, required=False)


class AdminDomainUpdateSerializer(serializers.Serializer):
    label = serializers.CharField(min_length=2, max_length=100, required=False)
    isActive = serializers.BooleanField(required=False)
    extensionStart = serializers.IntegerField(min_value=100, max_value=999999, required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("At least one field is required.")
        return attrs
