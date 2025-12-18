"""Content versioning service for proposal file management."""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models import ContentVersion, ProposalContent


class ContentVersioningService:
    """Service for managing proposal content and version history."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_content(
        self,
        proposal_id: int,
        file_path: str,
        content: str,
        user_id: int,
        change_reason: str | None = None,
    ) -> ProposalContent:
        """Save content and create version history entry.

        Args:
            proposal_id: ID of the proposal
            file_path: Relative file path (e.g., "proposal.md")
            content: File content
            user_id: ID of the user making the change
            change_reason: Optional reason for the change

        Returns:
            Updated ProposalContent record
        """
        # Find existing content or create new
        result = await self.session.execute(
            select(ProposalContent).where(
                ProposalContent.proposal_id == proposal_id,
                ProposalContent.file_path == file_path,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Create version history entry before updating
            version_entry = ContentVersion(
                proposal_id=proposal_id,
                file_path=file_path,
                content=existing.content,
                version=existing.version,
                created_by=existing.updated_by,
                created_at=existing.updated_at,
                change_reason=change_reason,
            )
            self.session.add(version_entry)

            # Update existing content
            existing.content = content
            existing.version += 1
            existing.updated_by = user_id
            existing.updated_at = datetime.utcnow()
            self.session.add(existing)
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        else:
            # Create new content entry
            new_content = ProposalContent(
                proposal_id=proposal_id,
                file_path=file_path,
                content=content,
                version=1,
                updated_by=user_id,
                updated_at=datetime.utcnow(),
            )
            self.session.add(new_content)
            await self.session.commit()
            await self.session.refresh(new_content)
            return new_content

    async def get_content(
        self,
        proposal_id: int,
        file_path: str,
    ) -> ProposalContent | None:
        """Get current content for a file.

        Args:
            proposal_id: ID of the proposal
            file_path: Relative file path

        Returns:
            ProposalContent or None if not found
        """
        result = await self.session.execute(
            select(ProposalContent).where(
                ProposalContent.proposal_id == proposal_id,
                ProposalContent.file_path == file_path,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_contents(self, proposal_id: int) -> list[ProposalContent]:
        """Get all content files for a proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of ProposalContent records
        """
        result = await self.session.execute(
            select(ProposalContent)
            .where(ProposalContent.proposal_id == proposal_id)
            .order_by(ProposalContent.file_path)
        )
        return list(result.scalars().all())

    async def get_version_history(
        self,
        proposal_id: int,
        file_path: str,
    ) -> list[ContentVersion]:
        """Get version history for a file.

        Args:
            proposal_id: ID of the proposal
            file_path: Relative file path

        Returns:
            List of ContentVersion records ordered by version descending
        """
        result = await self.session.execute(
            select(ContentVersion)
            .where(
                ContentVersion.proposal_id == proposal_id,
                ContentVersion.file_path == file_path,
            )
            .order_by(ContentVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_version(
        self,
        proposal_id: int,
        file_path: str,
        version: int,
    ) -> ContentVersion | None:
        """Get a specific version of a file.

        Args:
            proposal_id: ID of the proposal
            file_path: Relative file path
            version: Version number

        Returns:
            ContentVersion or None if not found
        """
        result = await self.session.execute(
            select(ContentVersion).where(
                ContentVersion.proposal_id == proposal_id,
                ContentVersion.file_path == file_path,
                ContentVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def rollback_to_version(
        self,
        proposal_id: int,
        file_path: str,
        version: int,
        user_id: int,
    ) -> ProposalContent:
        """Rollback content to a specific version.

        Args:
            proposal_id: ID of the proposal
            file_path: Relative file path
            version: Version number to rollback to
            user_id: ID of user performing rollback

        Returns:
            Updated ProposalContent

        Raises:
            ValueError: If version not found
        """
        # Get the target version
        target = await self.get_version(proposal_id, file_path, version)
        if target is None:
            raise ValueError(f"Version {version} not found for {file_path}")

        # Save with rollback reason
        return await self.save_content(
            proposal_id=proposal_id,
            file_path=file_path,
            content=target.content,
            user_id=user_id,
            change_reason=f"Rollback to version {version}",
        )

    async def delete_content(self, proposal_id: int, file_path: str) -> bool:
        """Delete content for a file (and its history).

        Args:
            proposal_id: ID of the proposal
            file_path: Relative file path

        Returns:
            True if deleted, False if not found
        """
        # Delete version history
        result = await self.session.execute(
            select(ContentVersion).where(
                ContentVersion.proposal_id == proposal_id,
                ContentVersion.file_path == file_path,
            )
        )
        for version in result.scalars().all():
            await self.session.delete(version)

        # Delete current content
        result = await self.session.execute(
            select(ProposalContent).where(
                ProposalContent.proposal_id == proposal_id,
                ProposalContent.file_path == file_path,
            )
        )
        content = result.scalar_one_or_none()
        if content:
            await self.session.delete(content)
            await self.session.commit()
            return True

        await self.session.commit()
        return False
